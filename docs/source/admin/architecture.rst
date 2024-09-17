.. _architecture:

============
Architecture
============

.. figure:: ../images/architecture.png
   :width: 80%
   :align: center
   :alt: Trainy

Konduktor was built with the following objectives in mind.

#. ML Engineers who can train on multi-gpu already should be able to scale across nodes with little to no code changes and bring their favorite frameworks (PyTorch, Lightning, HuggingFace, Deepspeed, etc.)
#. Support multi-tenancy and resource sharing via quotas
#. Observability and Auto-healing to gracefully handle GPU/hardware errors

which led to us building on `Kubernetes <https://kubernetes.io/>`_ as well as integrating with the following tools.

#. `SkyPilot <https://skypilot.readthedocs.io/en/latest/>`_ - supports easy scaleout over nodes with declarative resource requests

    .. code-block:: yaml
        :emphasize-lines: 4-4

        resources:
            accelerators: H100:8

        num_nodes: 100

        run: |
            num_nodes=`echo "$SKYPILOT_NODE_IPS" | wc -l`
            master_addr=`echo "$SKYPILOT_NODE_IPS" | head -n1`
            python3 -m torch.distributed.launch --nproc_per_node=$SKYPILOT_NUM_GPUS_PER_NODE \
            --nnodes=$num_nodes --node_rank=$SKYPILOT_NODE_RANK --master_addr=$master_addr \
            --master_port=8008 resnet_ddp.py --num_epochs 20


#. `Kueue <https://kueue.sigs.k8s.io/>`_ - declarative resource quotas, sharing, and job pre-emption via workload queues/priorities

    - ML Engineers only have to specify which queues they want to submit to
        .. code-block:: yaml
            :emphasize-lines: 4-5

            resources:
                accelerators: H100:8
                labels:
                    kueue.x-k8s.io/queue-name: user-queue # this is the same as the queue above
                    kueue.x-k8s.io/priority-class: high-priority # specify high-priority workload

            num_nodes: 100

            run: |
                num_nodes=`echo "$SKYPILOT_NODE_IPS" | wc -l`
                master_addr=`echo "$SKYPILOT_NODE_IPS" | head -n1`
                python3 -m torch.distributed.launch --nproc_per_node=$SKYPILOT_NUM_GPUS_PER_NODE \
                --nnodes=$num_nodes --node_rank=$SKYPILOT_NODE_RANK --master_addr=$master_addr \
                --master_port=8008 resnet_ddp.py --num_epochs 20

    - Cluster administrators can set GPU quotas by team via resource flavors and queues.
        .. code-block:: yaml
            :emphasize-lines: 27-28

            apiVersion: kueue.x-k8s.io/v1beta1
            kind: ResourceFlavor
            metadata:
            name: "default-flavor"
            ---
            apiVersion: kueue.x-k8s.io/v1beta1
            kind: ClusterQueue
            metadata:
            name: "cluster-queue"
            spec:
            preemption:
                reclaimWithinCohort: Any
                borrowWithinCohort:
                policy: LowerPriority
                maxPriorityThreshold: 100
                withinClusterQueue: LowerPriority
            namespaceSelector: {} # match all.
            resourceGroups:
            - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
                flavors:
                - name: "default-flavor"
                resources:
                - name: "cpu"
                    nominalQuota: 10000
                - name: "memory"
                    nominalQuota: 10000Gi
                - name: "nvidia.com/gpu"
                    nominalQuota: 8 # REPLACE THIS
            ---
            apiVersion: kueue.x-k8s.io/v1beta1
            kind: LocalQueue
            metadata:
            name: "user-queue"
            spec:
            clusterQueue: "cluster-queue"


#. `Prometheus <https://prometheus.io/>`_, `Grafana <https://grafana.com/oss/grafana/>`_, `OpenTelemetry <https://opentelemetry.io/>`_, `Loki <https://grafana.com/oss/loki/>`_: Exporters for both GPU metrics and kernel logs as well as metrics and logging backends for longer term storage and querying. Health controllers run in a loop to detect and cordon faulty nodes preventing jobs from landing on bad hardware repeatedly ensuring continuous delivery while cluster admins have immediate feedback on where & what is causing an alert from one location.