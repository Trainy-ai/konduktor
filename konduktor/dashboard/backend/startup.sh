#!/bin/bash

# Run kubectl port-forward in the background
# kubectl port-forward svc/loki -n loki 3100:3100 &  # Loki logs
# kubectl port-forward svc/kube-prometheus-stack-grafana -n prometheus 3000:80 &  # Prometheus Grafana dashboard

# Wait for background processes to ensure they are running
# sleep 5

# Start the backend service (Gunicorn)
gunicorn -w 1 --threads 2 -b 0.0.0.0:5001 main:app
