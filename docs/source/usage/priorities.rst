.. _priorities:

==============================
Job Priorities and Pre-emption
==============================

Job priority allows teams to enqueue development workloads, while enabling users to 
preempt lower priority resources to free up resources for mission critical high priority
workloads. This page explains to use job priorities with `Kueue <https://kueue.sigs.k8s.io/>`_ and `Skypilot <https://skypilot.readthedocs.io/en/latest/>`_.

This tutorial requires that you install:

- Trainy skypilot: :code:`pip install "trainy-skypilot-nightly[kubernetes]"`
- `kubectl <https://kubernetes.io/docs/reference/kubectl/>`_

---------------------------------------------
Example: Using Skypilot with Kueue Priorities
---------------------------------------------

Assuming your cluster administrator has provisioned GPU instances and given you 
quota within your cluster, you can request GPUs by specifying.

- Workload queue: :code:`kueue.x-k8s.io/queue-name: user-queue`
- Workload priority: :code:`kueue.x-k8s.io/priority-class: low-priority`

Let's define a request for a single :code:`T4:4` instance.

.. code-block:: yaml
    :emphasize-lines: 5-6

    # low.yaml
    resources:
        accelerators: T4:4
        labels:
            kueue.x-k8s.io/queue-name: user-queue # this is assigned by your admin
            kueue.x-k8s.io/priority-class: low-priority # specify low priority workload

    run: |
        echo "hi i'm a low priority job"
        sleep 1000000

and now you can launch the request

.. code-block:: console

    # launch a low priority task
    $ sky launch -y -d -c low task.yaml


    # list workloads in kueue
    $ kubectl get workloads
    NAME                 QUEUE        RESERVED IN     ADMITTED   FINISHED   AGE
    low-3ce1             user-queue                                         5m

While this workload is running we can enqueue another higher-priority task. If there is room in the cluster
to fulfill the higher priority workload by preempting lower priority jobs work, Kueue will delete the lower
priority workloads and launch the higher priority ones instead.

.. code-block:: yaml
    :emphasize-lines: 5-6

    # high.yaml
    resources:
        accelerators: T4:4
        labels:
            kueue.x-k8s.io/queue-name: user-queue # this is the same as the queue above
            kueue.x-k8s.io/priority-class: high-priority # specify high-priority workload

    run: |
        echo "hi i'm a high priority job"
        sleep 1000000


and now you can launch the request but now with high priority with.

.. code-block:: console

    # launch a development cluster 
    $ sky launch -y -d -c high high.yaml


    # list workloads in kueue
    $ kubectl get workloads
    NAME                 QUEUE        RESERVED IN     ADMITTED   FINISHED   AGE
    high-3ce1            user-queue                                         2m

.. tip::

    Pre-empted tasks are not by default requeued if you use :code:`sky launch`. To have your jobs retried,
    we recommend using :code:`sky jobs launch` instead so that when a task is pre-empted, the skypilot
    job controller will automatically resubmit your task to Kueue without manual intervention.

References
----------

- `The original guide <https://github.com/skypilot-org/skypilot/tree/k8s_kueue_example/examples/kueue>`_ by Romil Bhardwaj.
- `Kueue priority docs <https://kueue.sigs.k8s.io/docs/concepts/workload_priority_class/>`_

