// app/api/grafana/route.js

import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const response = await fetch(
      'http://kube-prometheus-stack-grafana.prometheus.svc.cluster.local:80/', 
      {
        headers: {
          'Content-Type': 'text/html',
        },
      }
    );

    // If the response is not ok, throw an error.
    if (!response.ok) {
      throw new Error(`Grafana returned ${response.status}: ${response.statusText}`);
    }

    const html = await response.text();
    return new NextResponse(html, {
      headers: {
        'Content-Type': 'text/html',
      },
    });

  } catch (error) {
    console.error('Error fetching Grafana:', error.message);
    return new NextResponse(
      `<h1>Error loading Grafana: ${error.message}</h1>`, 
      { status: 500, headers: { 'Content-Type': 'text/html' } }
    );
  }
}
