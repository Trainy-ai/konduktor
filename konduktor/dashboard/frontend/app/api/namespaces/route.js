import { NextResponse } from 'next/server';

const backendUrl = process.env.NODE_ENV === 'development'
    ? 'http://127.0.0.1:5001' // Development API
    : 'http://backend:5001' // Production API

// GET request for jobs
export async function GET() {
    try {
        // Forward request to backend API
        const response = await fetch(`${backendUrl}/getNamespaces`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
        })
    
        const data = await response.json()
        return new NextResponse(JSON.stringify(data))
    } catch (error) {
        console.error("Server get error:", error);
        return new NextResponse(error)
    }
}

  