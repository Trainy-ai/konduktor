.. _getting_started:

===============
Getting Started
===============

To get access to your Trainy: Konduktor clusters, work with your account manager to add all devices that
will require cluster access as client configurations in :code:`~/.sky/config.yaml`. 
Trainy provides isolated access to clusters via `Tailscale <https://tailscale.com/>`_, which you 
will need to `install <https://tailscale.com/kb/1347/installation>`_ on your development machine. 
You can see and connect to the clusters you have access to with:

.. code-block:: bash

    # list clusters
    $ tailscale status
    100.85.126.7  awesomecorp-laptop   awesomecorp-laptop.taila1933c.ts.net macOS  -
    100.95.60.42  awesomecorp-gke1     tagged-devices linux  idle, tx 39656 rx 1038824
    100.90.169.2  awesomecorp-gke2     tagged-devices linux  -

    # configure connection to a cluster
    $ tailscale configure kubeconfig awesomecorp-gke1 

    # check that k8s credentials work
    $ sky check
    Checking credentials to enable clouds for SkyPilot.
    Kubernetes: enabled

Once you are connected, you can start `running jobs <usage/quickstart.html>` on your cluster.

===================
Node Specifications
===================

Trainy managed Konduktor comes with clusters preconfigured and validated with the right drivers and software 
for running workloads on GPUs enabled with high-performance networking so you can start training
at scale without having to configure, autoscale, upgrade GPU infrastructure. The following clouds support
autoscaling:

- **GCP (a3-ultragpu), H100-80GB-MEGA:8, 1.6Tbps, 192vCPUs, 1TB RAM, 2TB disk** - **Available** ✅
- AWS on-demand/spot support, H100:8 3.2Tbps - In progress 🚧
- Azure on-demand/spot support, H100:8 3.2Tbps - In progress 🚧

On our autoscaling clusters, for now we only support :code:`H100:8` or :code:`H100-80GB-MEGA:8` instances, which
can be requested as.

.. code-block:: yaml

    num_nodes: 2 # scale up number of nodes

    resources:
        image_id: docker:nvcr.io/nvidia/pytorch:23.10-py3 # specify your image
        accelerators: H100-80GB-MEGA:8 # specify the right gpu type
        cpus: 192+ # 192 CPUs
        memory: 1000+ # 1TB of RAM
        cloud: kubernetes
        labels:
            kueue.x-k8s.io/queue-name: user-queue # this is assigned by your admin
            kueue.x-k8s.io/priority-class: low-priority

.. warning::

    Trainy instances are ephemeral and will be autoscaled down in 10 minutes of idling. Be sure if you are
    running stateful applications like model training to instrument your application to regularly
    retrieve and back up to object storage (S3, GCS, Azure Blob, Cloudflare R2, etc.)
