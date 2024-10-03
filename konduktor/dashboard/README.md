When kubectl is hooked up to remote machine

# apply kubernetes manifest
In manifests:
    kubectl apply -f dashboard_deployment.yaml

# port forward frontend
kubectl port-forward svc/frontend 5173:5173 -n default

# port forward backend
kubectl port-forward svc/backend 5001:5001 -n default
