.. _observability:

=============
Observability
=============

.. figure:: ../images/dashboard.png
   :width: 120%
   :align: center
   :alt: dashboard
   :class: no-scaled-link

Access Grafana
--------------

A local Grafana instance is deployed as part of the observability stack.
The dashboard shows an overview of the available GPUs, pending/active workloads, and over all cluster utilization.

.. code-block:: console

    # get the service name
    $ kubectl get svc -n prometheus | grep grafana
    kube-prometheus-stack-1717404158-grafana                    ClusterIP    10.122.81.251   <none>        80/TCP                    4d2h

We can use :code:`kubectl port-forward` to access the grafana service from our laptop. For the example above,

.. code-block:: console

    $ kubectl port-forward -n prometheus svc/kube-prometheus-stack-1717404158-grafana 3000:80

In the example above, we can enter :code:`https://localhost:3000` into a browser window where it will prompt for a password. 
The default username is :code:`admin` with the password being set by :code:`kube-prometheus-stack.values` in :doc:`/admin/installation`.
**Administrators should secure this endpoint as well as changing the authentication login.**

Metrics Dashboard
-----------------

After logging in, you can `import <https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/>`_ our default dashboard by either using the `JSON definition from the repo <https://github.com/Trainy-ai/konduktor/tree/main/grafana>`_ under :code:`grafana/default_grafana_dashboard.json`
or by downloading from `our Grafana published dashboard <https://grafana.com/grafana/dashboards/21231-konduktor/>`_.
A interactive sample dashboard can be found `here <https://snapshots.raintank.io/dashboard/snapshot/5x2e6d2A24Rkxdnu8ozpSgG4utXg1cZX>`_.

To track cluster GPU utilization, useful metrics to track include:

- GPU utilization
- GPU memory usage
- GPU SM efficiency

Multinode workloads performance benefits from tracking:

- NVLINK bandwidth
- Infiniband throughput (only for Infiniband networked setups)

For clusters with job queueing enabled we included:

- Jobs pending/active and number of GPUs requested
- Number of GPUs allocated vs free

Node level stats include:

- Disk usage
- CPU utilization

Reading Logs
------------

Grafana provides views for querying and filtering logs from pods and nodes. 
First `add Loki as a data source <https://grafana.com/docs/loki/latest/visualize/grafana/>`_,
setting the URL to be :code:`http://loki.loki.svc.cluster.local:3100` and create a new dashboard
with your newly created Loki datasource and begin querying your logs by node, namespace, etc.

.. figure:: ../images/otel-loki.png
   :width: 120%
   :align: center
   :alt: dashboard
   :class: no-scaled-link

