### Prereqs: kubectl is configured with remote machine/cluster

## 1. Apply kubernetes manifest
Inside manifests (one with dashboard_deployment.yaml):
```
kubectl apply -f dashboard_deployment.yaml
```

## 2. Port forward frontend and grafana
```
kubectl port-forward svc/frontend 5173:5173 -n default &
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus &
```

### v0.5 notes: only uses logs from k8s_namespace_name="loki" and only uses jobs from default namespace
