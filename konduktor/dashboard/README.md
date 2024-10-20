### Prereqs: kubectl is configured with remote machine/cluster

## 1. Apply kubernetes manifest
Inside manifests directory (one with dashboard_deployment.yaml):
```
kubectl apply -f dashboard_deployment.yaml
```

## 2. Port forward frontend and grafana
```
kubectl port-forward svc/frontend 5173:5173 -n konduktor-dashboard &
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus &
```

### v0.9 notes: only uses jobs from default namespace
