import { NextResponse } from 'next/server';

const backendUrl = process.env.NODE_ENV === 'development'
    ? 'http://127.0.0.1:5000' // Development API
    : 'http://backend:5001' // Production API

console.log('test route 1')

// GET request for jobs
export async function GET() {
    console.log('test route 2')
    try {
        console.log(`Server Component: Getting active namespaces`);
        
        // Forward request to backend API
        const response = await fetch(`${backendUrl}/getNamespaces`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            },
        })

        console.log(JSON.stringify(response))
    
        const data = await response.json()
        console.log(`Server Component getJobs: ${JSON.stringify(data)}`)
        return new NextResponse(JSON.stringify(data))
    } catch (error) {
        console.error("Server delete error:", error);
        return new NextResponse(error)
    }
}