.. _quickstart:

==========
Quickstart
==========

This section is for ML Engineers who need to run jobs on their k8s cluster. They will need a k8s admin to assign them a namespace
and queue for submitting jobs as well as a k8s config file to place into :code:`~/.kube/config` to give access to the cluster. Using `Skypilot <https://skypilot.readthedocs.io/en/latest/docs/index.html>`_ is going to be the easiest way to submit jobs. We maintain a fork of the original project to support Kueue for multi-node workloads. We are currently trying to get this upstreamed `here <https://github.com/skypilot-org/skypilot/pull/3543>`_

In managed Konduktor, we by default provision one queue

- :code:`user-queue` 

with two priority classes

- :code:`low-priority`
- :code:`high-priority`

Setup
------------

.. code-block:: bash

    # install trainy-skypilot
    $ conda create -n konduktor python=3.10
    $ pip install trainy-skypilot-nightly[kubernetes]

    # check that k8s credentials work
    $ sky check
    Checking credentials to enable clouds for SkyPilot.
    Kubernetes: enabled

and create the following in :code:`~/.sky/config.yaml`

.. code-block:: yaml

    kubernetes:
        remote_identity: SERVICE_ACCOUNT
        provision_timeout: -1

Hello Konduktor
---------------

To create a development environment, let's first define our resource request as :code:`task.yaml`

.. code-block:: yaml

    resources:
        image_id: docker:nvcr.io/nvidia/pytorch:23.10-py3
        accelerators: T4:4
        cpus: 8+
        memory: 8+
        cloud: kubernetes
        # (optional) use resource queues if cluster admin set them
        labels:
            kueue.x-k8s.io/queue-name: user-queue # this is assigned by your admin
            kueue.x-k8s.io/priority-class: low-priority

The :code:`kueue.x-k8s.io` labels are required in order to run if your cluster admin created resource queues. 
To issue this request run:

.. code-block:: console

    # create a request
    $ sky launch -c dev task.yaml

    # login to dev container
    $ ssh dev

    # list running clusters
    $ sky status

    # tear down cluster once you are down using it
    $ sky down dev

Distributed Jobs
----------------

To scale up the job size over multiple nodes, we just change :code:`task.yaml` to specify :code:`num_nodes`.
We define a script for each node to run by using the :code:`setup` and :code:`run` sections.

.. code-block:: yaml
    :emphasize-lines: 12-12,22-23,25-25

    resources:
        image_id: docker:nvcr.io/nvidia/pytorch:23.10-py3
        accelerators: T4:4
        cpus: 8+
        memory: 8+
        cloud: kubernetes
        # (optional) use resource queues if cluster admin set them
        labels:
            kueue.x-k8s.io/queue-name: user-queue # this is assigned by your admin
            kueue.x-k8s.io/priority-class: high-priority # this will preempt low-priority jobs

    num_nodes: 2

    setup: |
        git clone https://github.com/roanakb/pytorch-distributed-resnet
        cd pytorch-distributed-resnet
        mkdir -p data  && mkdir -p saved_models && cd data && \
        wget -c --quiet https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz
        tar -xvzf cifar-10-python.tar.gz
    
    run: |
        num_nodes=`echo "$SKYPILOT_NODE_IPS" | wc -l`
        master_addr=`echo "$SKYPILOT_NODE_IPS" | head -n1`
        python3 -m torch.distributed.launch --nproc_per_node=$SKYPILOT_NUM_GPUS_PER_NODE \
        --nnodes=$num_nodes --node_rank=$SKYPILOT_NODE_RANK --master_addr=$master_addr \
        --master_port=8008 resnet_ddp.py --num_epochs 20

and run with

.. code-block:: console

    # create a job that runs in the background
    $ sky jobs launch -d -c distributed --detach-run task.yaml

    # show the status of all existing jobs
    $ sky jobs queue

    # cancel a running or pending job
    $ sky jobs cancel <JOB_ID>

This will create a managed job that will run in the background to completion.

For a more thorough explanation of all of Skypilot's capabilities, please refer to the `documentation <https://skypilot.readthedocs.io/en/latest>`_ and `examples <https://github.com/skypilot-org/skypilot/tree/master/examples>`_.
Below are a series of links to explain some of the commonly used capabilities of Skypilot relevant for running batch/training jobs.

------------------
Skypilot Reference
------------------

- `Distributed training <https://skypilot.readthedocs.io/en/latest/running-jobs/environment-variables.html>`_
- `Managed Jobs <https://skypilot.readthedocs.io/en/latest/examples/managed-jobs.html>`_
- `Skypilot FAQ <https://skypilot.readthedocs.io/en/latest/reference/faq.html>`_
- `Syncing code and artifacts to training clusters <https://skypilot.readthedocs.io/en/latest/examples/syncing-code-artifacts.html>`_
- `Environment variables <https://skypilot.readthedocs.io/en/latest/running-jobs/environment-variables.html>`_
- `Autodown on task completion <https://skypilot.readthedocs.io/en/latest/reference/auto-stop.html>`_
- `Skypilot CLI spec <https://skypilot.readthedocs.io/en/latest/reference/cli.html>`_
- `Skypilot task.yaml spec <https://skypilot.readthedocs.io/en/latest/reference/yaml-spec.html>`_
- `Skypilot Python API <https://skypilot.readthedocs.io/en/latest/reference/api.html>`_
