.. Konduktor documentation master file, created by
   sphinx-quickstart
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Konduktor's documentation!
=====================================

.. figure:: ./images/konduktor-logo-white-no-background.png
   :width: 60%
   :align: center
   :alt: Trainy
   :class: no-scaled-link, only-dark

.. figure:: ./images/konduktor-logo-black-no-background.png
   :width: 60%
   :align: center
   :alt: Trainy
   :class: no-scaled-link, only-light

.. raw:: html

   <p style="text-align:center">
   <a class="reference external image-reference" style="vertical-align:9.5px" href="https://discord.com/invite/HQUBJSVgAP"><img src="https://dcbadge.vercel.app/api/server/d67CMuKY5V" style="height:27px"></a>
   <script async defer src="https://buttons.github.io/buttons.js"></script>
   <a class="github-button" href="https://github.com/Trainy-ai/konduktor" data-show-count="true" data-size="large" aria-label="Star Konduktor on GitHub">Star</a>
   </p>

   <p style="text-align:center">
   <strong>Batch Jobs and Cluster Management for GPUs on Kubernetes</strong>
   </p>

Konduktor is a platform designed for running ML batch jobs and managing GPU clusters. 
This documentation is targeted towards:

- ML Engineers/researchers trying to launch training jobs on Konduktor, either managed by `Trainy <https://trainy.ai/>`_ or self-hosted
- GPU cluster administrators trying to self-host Konduktor

For interest in our managed offering, please contact us at support@trainy.ai

------------
Key Features
------------

- 🚀 Easily scale out and job queueing and multi-node scheduling

.. code-block:: shell

   # create a request
   $ sky launch -c dev task.yaml --num-nodes 100

- ☁ Multi-cloud access

.. code-block:: shell

   # toggle cluster via region
   $ sky launch -c dev task.yaml --region gke-cluster

- Custom container support

.. code-block:: yaml

   # task.yaml
   resources:
      image_id: docker:nvcr.io/nvidia/pytorch:23.10-py3

   run: |
      python train.py

- `Track active and pending jobs and utilization, power usage, etc. <admin/observability.html>`_

----------------------------
Managed Features and Roadmap
----------------------------
- On-prem/reserved support - **Available** ✅
- GCP on-demand/spot support - **Available** ✅
- AWS on-demand/spot support - In progress 🚧
- Azure on-demand/spot support - In progress 🚧
- Multi-cluster submission - In progress 🚧

Documentation
-------------

.. toctree::
   :maxdepth: 1
   :caption: Managed Konduktor

   cloud/getting_started

.. toctree::
   :maxdepth: 1
   :caption: Job Scheduling

   usage/quickstart
   usage/priorities

.. toctree::
   :maxdepth: 1
   :caption: Self-hosted Cluster Administration
   
   admin/installation
   admin/observability
   admin/controller
   admin/architecture
   

External Links
--------------------------

- `Trainy Developer Blog <https://trainy.ai/blog>`_

This project is powered by:

- `SkyPilot <https://skypilot.readthedocs.io/en/latest/>`_
- `Kueue <https://kueue.sigs.k8s.io/>`_
- `Prometheus <https://prometheus.io/>`_
- `Grafana <https://grafana.com/oss/grafana/>`_
- `OpenTelemetry <https://opentelemetry.io/>`_
- `Kubernetes <https://kubenetes.io>`_