.. _installation:

============
Installation
============

This section is for k8s admins who are first deploying the necessary resources onto their k8s cluster. The Konduktor stack consists of the following components:

- `DCGM Exporter <https://github.com/NVIDIA/dcgm-exporter>`_ - Exporting GPU health metrics and managing node lifecycle
- `kube-prometheus-stack <https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack>`_ - Deploy Prometheus & Grafana stack for observability
- `Loki <https://grafana.com/oss/loki/>`_ - Logging aggregration endpoint
- `OpenTelemetry <https://opentelemetry.io/>`_ - Log publishing
- `Kueue <https://kueue.sigs.k8s.io/>`_ - workload scheduling and resource quotas/sharing

For a more thorough explanation of the Konduktor stack, see :doc:`architecture`

Prerequisites
=============

Before starting, make sure that you have:

- A Kubernetes cluster (1.28+)
- :code:`kubectl`
- `Helm <https://helm.sh/>`_

Observability
=============

DCGM Installation
-----------------

Installing the DCGM exporter is best handled using NVIDIA's `gpu-operator <https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/index.html>`_. To install, you can run:

.. code-block:: bash

    # add nvidia repo
    $ helm repo add nvidia https://helm.ngc.nvidia.com/nvidia \
        && helm repo update

    # create the `gpu-operator` namespace
    $ kubectl create namespace gpu-operator

    # set which metrics to export from DCGM
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/files/dcgm-metrics.csv
    $ vim dcgm-metrics.csv
    $ kubectl create configmap metrics-config -n gpu-operator --from-file=dcgm-metrics.csv

    # install gpu operator
    $ helm install gpu-operator -n gpu-operator \
        nvidia/gpu-operator $HELM_OPTIONS \
        --set dcgmExporter.config.name=metrics-config \
        --set dcgmExporter.env[0].name=DCGM_EXPORTER_COLLECTORS \
        --set dcgmExporter.env[0].value=/etc/dcgm-exporter/dcgm-metrics.csv


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

.. tip::

    This guide currently works for on-prem bare metal deployments.
    We are still validating on how to deploy :code:`nvidia-dcgm-exporter` 
    on managed k8s solutions like AWS's **EKS** and Google's **GKE**. Stay tuned for updates!

Prometheus-Grafana Stack
------------------------

To setup the monitoring stack, we're maintaining our own `default values to get started with <https://github.com/Trainy-ai/konduktor/blob/main/manifests/kube-prometheus-stack.values>`_.

.. code-block:: bash

    # get default values for Helm chart
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/kube-prometheus-stack.values

    # add promtheus-community repo 
    $ helm repo add prometheus-community \
        https://prometheus-community.github.io/helm-charts

    # install prometheus stack
    $ helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
        --create-namespace \ 
        --namespace prometheus \
        --values kube-prometheus-stack.values 

    # check prometheus stack is up
    $ kubectl get pods -n prometheus
    NAME                                                      READY   STATUS    RESTARTS   AGE
    alertmanager-kube-prometheus-stack-alertmanager-0         2/2     Running   0          53s
    kube-prometheus-stack-grafana-79f9ccf77-wccpt             3/3     Running   0          56s
    kube-prometheus-stack-kube-state-metrics-b7b54458-klcb4   1/1     Running   0          56s
    kube-prometheus-stack-operator-74774b4dbd-bdzsr           1/1     Running   0          56s
    kube-prometheus-stack-prometheus-node-exporter-74245      1/1     Running   0          57s
    kube-prometheus-stack-prometheus-node-exporter-8t5ct      1/1     Running   0          56s
    kube-prometheus-stack-prometheus-node-exporter-bp8cb      1/1     Running   0          57s
    kube-prometheus-stack-prometheus-node-exporter-ttj5b      1/1     Running   0          56s
    kube-prometheus-stack-prometheus-node-exporter-z8rzn      1/1     Running   0          57s
    prometheus-kube-prometheus-stack-prometheus-0             2/2     Running   0          53s

    
OpenTelemetry-Loki Logging Stack
--------------------------------

For setting up a monolithic Loki stack with exported node/pod metrics, we include some default values for installing
the stack via Helm. We also deploy a daemonset to stream dmesg logs from each node.

.. code-block:: bash

    # get Helm chart values
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/loki.values
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/otel.values

    $ helm repo add grafana https://grafana.github.io/helm-charts
    $ helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
    $ helm repo update

    $ helm install loki grafana/loki \
        --create-namespace \
        --namespace=loki \
        --values loki.values
    $ helm install otel-collector open-telemetry/opentelemetry-collector \
        --create-namespace \
        --namespace=otel-collector \
        --values otel.values
    $ kubectl apply -f https://raw.githubusercontent.com/Trainy-ai/konduktor/main/konduktor/manifests/dmesg_daemonset.yaml

    $ kubectl get pods -n loki
    NAME                                                 READY   STATUS    RESTARTS   AGE
    loki-0                                               1/1     Running   0          35m
    loki-canary-26rw2                                    1/1     Running   0          35m
    loki-chunks-cache-0                                  2/2     Running   0          35m
    loki-gateway-68fd56bfbd-ltnqd                        1/1     Running   0          35m
    loki-results-cache-0                                 2/2     Running   0          35m

    $ kubectl get pods -n otel-collector
    NAME                                                 READY   STATUS    RESTARTS   AGE
    otel-collector-opentelemetry-collector-agent-2qbh2   1/1     Running   0          31m

    $ kubectl get pods -n dmesg-logging
    NAME          READY   STATUS    RESTARTS   AGE
    dmesg-2x225   1/1     Running   0          5m52s


Scheduling & Resource Quotas (Optional)
=======================================

For job queueing and resource sharing cluster-wide, you can install Kueue and set resource quotas and queues.

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

Resource quotas are defined via ClusterQueues and LocalQueues which are assigned to a namespace. We provide a default set of resource definitions to get started with.

.. code-block:: bash

    # get default resource definitions
    $ wget https://raw.githubusercontent.com/Trainy-ai/konduktor/main/manifests/single-clusterqueue-setup.yaml

Within :code:`single-clusterqueue-setup.yaml`, be sure to replace :code:`<num-GPUs-in-cluster>` with the total number of GPUs in your cluster.

.. code-block:: yaml
    :emphasize-lines: 28-28

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
            nominalQuota: <num-GPUs-in-cluster> # REPLACE THIS
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
    $ kubectl apply -f single-clusterqueue-setup.yaml

    $ kubectl get queues
    NAME         CLUSTERQUEUE    PENDING WORKLOADS   ADMITTED WORKLOADS
    user-queue   cluster-queue   0                   0

