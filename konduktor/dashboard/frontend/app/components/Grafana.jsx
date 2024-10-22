'use client'
import { useState, useRef } from 'react';
import BarLoader from "react-spinners/BarLoader";


function Grafana() {

    const [isIframeLoaded, setIsIframeLoaded] = useState(false);
    const [isError, setIsError] = useState(false);
    const iframeRef = useRef(null);

    console.log(`loaded: ${isIframeLoaded}`)
    console.log(`error: ${isError}`)
  
    const handleLoad = () => {
        setIsIframeLoaded(true);
        setIsError(false);
    };

    const handleError = () => {
        setIsError(true);
        setIsIframeLoaded(false);
    };

    return (
        <div>
            {!isIframeLoaded ?
                <div style={{ display: 'flex', justifyContent: 'center', flexDirection: 'column', alignItems: 'center', marginTop: '48px' }}>
                    <p style={{ fontFamily: 'Poppins', fontSize: '22px', marginBottom: '24px' }}>Loading Grafana Konduktor Dashboard</p>
                    <BarLoader
                        height={8}
                        width={400}
                        aria-label="Loading Spinner"

                    />
                    <p style={{ fontFamily: 'Poppins', fontSize: '18px', marginTop: '24px' }}>If stuck loading, check port forwarding for errors</p>
                    <p style={{ fontFamily: 'Poppins', fontSize: '12px' }}>kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus</p>
                </div>
            :
                null    
            }
            {isError ?
                <div style={{ display: 'flex', justifyContent: 'center', flexDirection: 'column', alignItems: 'center', marginTop: '48px' }}>
                    <p style={{ fontFamily: 'Poppins', fontSize: '22px' }}>Error Loading Grafana Konduktor Dashboard</p>
                    <p style={{ fontFamily: 'Poppins', fontSize: '22px', marginTop: '32px' }}>Check port forwarding for errors</p>
                    <p style={{ fontFamily: 'Poppins', fontSize: '12px' }}>kubectl port-forward svc/kube-prometheus-stack-grafana 3000:80 -n prometheus</p>
                </div>
            :
                null
            }
            <iframe
                src='http://localhost:3000/dashboards'
                style={{
                    width: '100%',
                    height: '800px',
                    border: 'none',
                    visibility: isIframeLoaded ? 'visible' : 'hidden', // Control visibility
                    transition: 'visibility 0s, opacity 0.5s linear', // Smooth transition
                    opacity: isIframeLoaded ? 1 : 0, // Fade in effect
                }}
                title="Grafana Dashboard"
                onLoad={handleLoad}
                onError={handleError}
                ref={iframeRef}
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