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

// DELETE request for job deletion
export async function DELETE(req) {
    try {
        const { name, namespace } = await req.json(); // Parse the request body

        // Forward request to backend API
        const response = await fetch(`${backendUrl}/deleteJob`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, namespace })
        })

        const data = await response.json()
        return new NextResponse(JSON.stringify(data))
    } catch (error) {
        console.error("Server delete error:", error);
        return new NextResponse(error)
    }
}

// PUT request for updating job priority
export async function PUT(req) {
    try {
        const { name, namespace, priority, priority_class_name } = await req.json(); // Parse the request body

        // Forward request to backend API
        const response = await fetch(`${backendUrl}/updatePriority`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, namespace, priority, priority_class_name })
        })

        const data = await response.json()
        return new NextResponse(JSON.stringify(data))
    } catch (error) {
        console.error("Server update error:", error);
        return new NextResponse(error)
    }
}
  