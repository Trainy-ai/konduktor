.. _observability:

Observability
=============

.. figure:: ../images/dashboard.png
   :width: 120%
   :align: center
   :alt: dashboard
   :class: no-scaled-link

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
The default username is :code:`admin` with the password being set by :code:`kube-prometheus-stack.values` in :doc:`/getting-started/installation`.
**Administrators should secure this endpoint as well as changing the authentication login.**

After logging in, you can import our default dashboard by either using the JSON definition from the repo under :code:`grafana/default_grafana_dashboard.json`
or by downloading from `our Grafana published dashboard <https://grafana.com/grafana/dashboards/21231-konduktor/>`_.
An interactive sample dashboard can be found `here <https://snapshots.raintank.io/dashboard/snapshot/aUOb6ZQzCheglWM84xTAvqwX4zQHTaUf?orgId=0>`_.
