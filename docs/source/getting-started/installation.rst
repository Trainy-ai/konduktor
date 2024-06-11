.. _installation:

Installation
============

This section is for k8s admins who are first deploying the necessary resources onto their k8s cluster. The Konduktor stack consists of 3 main components:

- `DCGM Exporter <https://github.com/NVIDIA/dcgm-exporter>`_ - Exporting GPU health metrics and managing node lifecycle
- `kube-prometheus-stack <https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack>`_ - Deploy Prometheus & Grafana stack for observability
- `Kueue <https://kueue.sigs.k8s.io/>`_ - workload scheduling and resource quotas/sharing

Prerequisites
-------------

Before starting, make sure that you have:

- A Kubernetes cluster (1.28+)
- :code:`kubectl`
- `Helm <https://helm.sh/>`_

DCGM Installation
-----------------

Installing the DCGM exporter is best handled using NVIDIA's `gpu-operator <https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html>`_. To install, you can run:

.. code-block:: bash

    # add nvidia repo
    $ helm repo add nvidia https://helm.ngc.nvidia.com/nvidia \
        && helm repo update

    # install gpu operator
    $ helm install gpu-operator -n gpu-operator \
        --create-namespace nvidia/gpu-operator $HELM_OPTIONS

    # wait for pods to come up
    $ kubectl get pods -n gpu-operator
    NAME                                                              READY   STATUS      RESTARTS        AGE
    gpu-feature-discovery-b96rm                                       1/1     Running     0               9d
    gpu-operator-1716420454-node-feature-discovery-master-5bf9ts44g   1/1     Running     0               4d10h
    gpu-operator-1716420454-node-feature-discovery-worker-jlr26       1/1     Running     5 (4d10h ago)   14d
    gpu-operator-647d5bddf8-p6px2                                     1/1     Running     0               4d10h
    nvidia-container-toolkit-daemonset-tpncr                          1/1     Running     0               14d
    nvidia-cuda-validator-mmb4h                                       0/1     Completed   0               9d
    nvidia-dcgm-exporter-m7544                                        1/1     Running     0               9d
    nvidia-device-plugin-daemonset-lc5lx                              1/1     Running     0               14d
    nvidia-driver-daemonset-fvx9z                                     1/1     Running     0               9d
    nvidia-operator-validator-62dhx                                   1/1     Running     0               14d

Prometheus Stack
----------------

To setup the monitoring stack, we're maintaining our own `default values to get started with <https://github.com/Trainy-ai/konduktor/blob/main/manifests/kube-prometheus-stack.values>`_.

.. code-block:: bash

    # get default values for Helm chart
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/kube-prometheus-stack.values

    # add promtheus-community repo 
    $ helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts

    # install prometheus stack
    $ helm install prometheus-community/kube-prometheus-stack --create-namespace \
        --create-namespace \
        --namespace prometheus \
        --generate-name \
        --values kube-prometheus-stack.values

    # check prometheus stack is up
    $ kubectl get pods -n prometheus
    NAME                                                              READY   STATUS    RESTARTS   AGE
    alertmanager-kube-prometheus-stack-1717-alertmanager-0            2/2     Running   0          3d15h
    kube-prometheus-stack-1717-operator-6d9487489d-2vx8l              1/1     Running   0          3d15h
    kube-prometheus-stack-1717404158-grafana-6d48845b9-qf5qr          3/3     Running   0          3d15h
    kube-prometheus-stack-1717404158-kube-state-metrics-7c97ffbfxzt   1/1     Running   0          3d15h
    kube-prometheus-stack-1717404158-prometheus-node-exporter-2vh6j   1/1     Running   0          3d15h
    kube-prometheus-stack-1717404158-prometheus-node-exporter-68ldt   1/1     Running   0          3d15h
    kube-prometheus-stack-1717404158-prometheus-node-exporter-frd65   1/1     Running   0          3d15h
    kube-prometheus-stack-1717404158-prometheus-node-exporter-mxhpb   1/1     Running   0          3d15h
    prometheus-kube-prometheus-stack-1717-prometheus-0                2/2     Running   0          3d15h

Kueue
-----

To deploy Kueue components, we provide a default manifest for that enables gang-scheduling in addition to other options for telemetry.

.. code-block:: bash

    # deploy kueue resources
    $ VERSION=v0.6.2
    $ kubectl apply --server-side -f https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/manifests.yaml
    $ kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/$VERSION/prometheus.yaml
    $ kubectl apply --server-side -f https://github.com/kubernetes-sigs/kueue/releases/download/$VERSION/visibility-api.yaml

    # check kueue-system up
    $ kubectl get pods -n kueue-system
    NAME                                        READY   STATUS    RESTARTS   AGE
    kueue-controller-manager-6f4db9964d-rc6jk   2/2     Running   0          4d

Resource Quotas
---------------

Resource quotas are defined via ClusterQueues and LocalQueues which are assigned to a namespace. For example, we can define the following resources.

.. code-block:: yaml

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
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu", "smarter-devices/fuse"]
        flavors:
        - name: "default-flavor"
        resources:
        - name: "cpu"
            nominalQuota: 10000
        - name: "memory"
            nominalQuota: 10000Gi
        - name: "nvidia.com/gpu"
            nominalQuota: 16
        # this is a skypilot specific resource
        - name: "smarter-devices/fuse"
            nominalQuota: 10000000
    ---
    apiVersion: kueue.x-k8s.io/v1beta1
    kind: LocalQueue
    metadata:
    name: "user-queue"
    spec:
    clusterQueue: "cluster-queue"
    ---
    apiVersion: kueue.x-k8s.io/v1beta1
    kind: WorkloadPriorityClass
    metadata:
    name: low-priority
    value: 100  # Higher value means higher priority
    description: "Low priority experiments"
    ---
    apiVersion: kueue.x-k8s.io/v1beta1
    kind: WorkloadPriorityClass
    metadata:
    name: high-priority
    value: 1000
    description: "High priority production workloads"

We can create these resources with:

.. code-block:: console
    
    # create a ClusterQueue and LocalQueue, `cluster-queue` and `user-queue` respectively
    $ kubectl apply -f https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/single-clusterqueue-setup.yaml

    $ kubectl get queues
    NAME         CLUSTERQUEUE    PENDING WORKLOADS   ADMITTED WORKLOADS
    user-queue   cluster-queue   0                   0

