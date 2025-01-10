#!/bin/bash

# Function to check if a deployment is running
check_deployment_running() {
    local namespace=$1
    local deployment=$2
    kubectl get deployment "$deployment" -n "$namespace" -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' 2>/dev/null
}

# Check if frontend, backend, and Grafana deployments are running
frontend_status=$(check_deployment_running konduktor-dashboard frontend)
backend_status=$(check_deployment_running konduktor-dashboard backend)
grafana_status=$(check_deployment_running prometheus kube-prometheus-stack-grafana)

if [[ "$frontend_status" == "True" && "$backend_status" == "True" && "$grafana_status" == "True" ]]; then
    echo "All required deployments are already running. Skipping 'kubectl apply'."
else
    # Apply Kubernetes manifest if any deployment is not fully running
    echo "Applying Kubernetes manifest..."
    kubectl apply -f ./konduktor/manifests/dashboard_deployment.yaml

    # Wait for each deployment to be available
    echo "Waiting for frontend deployment to be available..."
    kubectl wait --for=condition=available deployment/frontend -n konduktor-dashboard --timeout=120s

    echo "Waiting for backend deployment to be available..."
    kubectl wait --for=condition=available deployment/backend -n konduktor-dashboard --timeout=120s

    echo "Waiting for Grafana deployment to be available..."
    kubectl wait --for=condition=available deployment/kube-prometheus-stack-grafana -n prometheus --timeout=120s

    # Wait 10 seconds to ensure pods are up and ready
    echo "Waiting for pods to finish setup..."
    sleep 10
fi

# Port-forward frontend and Grafana in the background
echo "Port-forwarding frontend (5173:5173)..."
kubectl port-forward svc/frontend 5173:5173 -n konduktor-dashboard &

echo "Port-forwarding Grafana (3000:80)..."
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus &

sleep 2

# Display the dashboard availability message
echo -e "\n================================================"
echo "Dashboard is available at http://localhost:5173/"
echo "================================================"
echo -e "\n"

# Keep the script running to hold the port-forward processes open
wait
