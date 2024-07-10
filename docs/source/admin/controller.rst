.. _controller:

======================
Node Health Controller
======================

Konduktor ships with a controller that listens to node logs for GPU related errors. Oftentimes, errors from
NCCL, CUDA, or GPUs point to persistent errors in the hardware. In this situation, in order to prevent workloads
from using bad nodes, we taint them so the kube-scheduler doesn't place any new pods on them.
Currently we listen for these `NVIDIA errors <https://docs.nvidia.com/deploy/xid-errors/index.html>`_:

- Xid errors
- SXid errors

And we listen for errors from:

- :code:`dmesg`

Controller Launch
=================

The controller runs as a loop and can be run from any machine with access to the k8s API server. The control loop:

- Queries the logging backend (Loki) for GPU related errors
- If an error is found, the affected node is tainted with :code:`trainy.konduktor.ai/faulty=true:NoSchedule` via the k8s API

Incluster Controller
--------------------

The controller can be shipped as a deployment that runs within the cluster. To deploy it:

.. code-block:: console

    # create the controller deployment 
    $ kubectl apply -f konduktor/manifests/controller_deployment.yaml

    # tail the logs of the deployment
    $ kubectl logs -f deployment/konduktor-controller-deployment -n konduktor

Remote Controller
-----------------

We can launch the controller locally from a machine with external access to the API server with:

.. code-block:: console

    # install konduktor package
    $ pip install konduktor-nightly

    # get local access to the loki service
    $ kubectl port-forward svc/loki -n loki 3100:3100 &

    # run the controller locally 
    $ LOG_ENDPOINT='http://localhost:3100' python -m konduktor.controller.launch
    I 07-09 04:51:21 parse.py:24] using POD_LOG_TYPE = skypilot

Controller Node Taint Test (Optional)
-------------------------------------

We can mock having a GPU error by writing to :code:`dmesg` directly. We can do this through
the :code:`dmesg-logging` DaemonSet which runs as privileged containers. In a separate terminal,
while the controller is running:

.. code-block:: console

    # get the name of a dmesg-logging pod
    $ kubectl get pods -n dmesg-logging
    NAME          READY   STATUS    RESTARTS   AGE
    dmesg-2x225   1/1     Running   0          10h

    $ kubectl exec -it dmesg-2x225 -- bash
    $ echo "[1235733.431527] NVRM: Xid (PCI:0000:4e:00): 79, pid='<unknown>', name=<unknown>, GPU has fallen off the bus." > /dev/kmsg

After which you should see in your controller logs

.. code-block:: console

    [I 07-09 05:37:45 parse.py:128] node `gke-a3-cluster-gpu-pool-2d164072-zz64` has dmesg error: [538441.007373] [1235733.431527] NVRM: Xid (PCI:0000:4e:00): 79, pid='<unknown>', name=<unknown>, GPU has fallen off the bus.
    [W 07-09 05:37:45 kube_client.py:27] incluster config failed to load, attempting to use kubeconfig.
    [I 07-09 05:37:45 kube_client.py:31] KUBECONFIG loaded
    [I 07-09 05:37:45 node.py:98] Node gke-a3-cluster-gpu-pool-2d164072-zz64 tainted.

    # in a separate terminal you can verify
    $ kubectl describe pod gke-a3-cluster-gpu-pool-2d164072-zz64 | grep trainy
    trainy.konduktor.ai/faulty=true:NoSchedule

You can remove all the taints in the cluster with :code:`konduktor reset`

.. code-block:: console

    (konduktor) Andrews-MacBook-Air:docs asai$ konduktor reset
    [W 07-09 05:38:14 kube_client.py:27] incluster config failed to load, attempting to use kubeconfig.
    [I 07-09 05:38:14 kube_client.py:31] KUBECONFIG loaded
    [I 07-09 05:38:15 node.py:64] Node gke-a3-cluster-cpu-pool-2d164072-zz64 taint removed.
    [I 07-09 05:38:15 node.py:64] Node gke-a3-cluster-default-pool-60f92594-0nm7 taint removed.
    [I 07-09 05:38:15 node.py:64] Node gke-a3-cluster-default-pool-60f92594-rfg8 taint removed.
    [I 07-09 05:38:15 node.py:64] Node gke-a3-cluster-default-pool-60f92594-xvvx taint removed.
    [I 07-09 05:38:16 node.py:64] Node gke-a3-cluster-t4-nodepool-528edcef-fl02 taint removed.

Features and Roadmap
====================
- :code:`dmesg` error detection - **Available**
- In-cluster deployment of controller - In progress
- Pod log error detection - In progress
- Health Checks (Taint Removal) - In progress
- Node Resolution Hooks (Reboot, Power Cycle) - In progress