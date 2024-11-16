### Prereqs: kubectl is configured with remote machine/cluster

# OPTION 1 (Automated Setup)

To open the dashboard, run this inside the root konduktor directory:
```
./start_dashboard.sh
```

# OPTION 2 (Manual Setup)

## 1. Apply kubernetes manifest
Inside manifests directory (one with dashboard_deployment.yaml):
```
kubectl apply -f dashboard_deployment.yaml
```
Then, wait a minute or two for the pods to finish setup

## 2. Port forward frontend in a terminal
```
kubectl port-forward svc/frontend 5173:5173 -n konduktor-dashboard
```

## 3. Port forward grafana in a terminal
```
kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus
```

## 4. Open dashboard at http://localhost:5173/

