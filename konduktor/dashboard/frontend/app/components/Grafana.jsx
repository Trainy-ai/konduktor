import React from 'react'

function Grafana() {

    return (
        <div>
            <iframe
                src='http://localhost:3000/dashboards'
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard"
            />
            {/*
            <iframe
                src='http://kube-prometheus-stack-grafana.prometheus.svc.cluster.local:3000/dashboards'  // Proxying the Grafana content through your server
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard2"
            />
            <iframe
                src='http://127.0.0.1:3000/dashboards'  // Proxying the Grafana content through your server
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard3"
            />
            <iframe
                src='http://localhost:80/dashboards'  // Proxying the Grafana content through your server
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard4"
            />
            <iframe
                src='http://127.0.0.1:80/dashboards'  // Proxying the Grafana content through your server
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard5"
            />
            <iframe
                src='http://kube-prometheus-stack-grafana.prometheus.svc.cluster.local:80/dashboards'  // Proxying the Grafana content through your server
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard6"
            />
            <iframe
                src="/api/grafana"
                style={{ width: '100%', height: '800px', border: 'none' }}
                title="Grafana Dashboard7"
            />
            */}
        </div>
    )
}

export default Grafana