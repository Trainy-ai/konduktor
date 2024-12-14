from typing import Any, Dict, List

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from konduktor import logging as konduktor_logging
from konduktor.kube_client import batch_api, core_api, crd_api

from .sockets import socketio as sio

logger = konduktor_logging.get_logger(__name__)

# FastAPI app
app = FastAPI()


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Use Kubernetes API clients
# Initialize BatchV1 and CoreV1 API (native kubernetes)
batch_client = batch_api()
core_client = core_api()
# Initialize Kueue API
crd_client = crd_api()


@app.get("/")
async def home():
    return JSONResponse({"home": "/"})


@app.delete("/deleteJob")
async def delete_job(request: Request):
    data = await request.json()
    name = data.get("name", "")
    namespace = data.get("namespace", "default")

    try:
        delete_options = client.V1DeleteOptions(propagation_policy="Background")

        crd_client.delete_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name,
            body=delete_options,
        )
        logger.debug(f"Kueue Workload '{name}' deleted successfully.")

        return JSONResponse({"success": True, "status": 200})

    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=e.status)


@app.get("/getJobs")
async def get_jobs():
    rows = fetch_jobs()
    return JSONResponse(rows)


@app.get("/getNamespaces")
async def get_namespaces():
    try:
        # Get the list of namespaces
        namespaces = core_client.list_namespace()
        # Extract the namespace names from the response
        namespace_list = [ns.metadata.name for ns in namespaces.items]
        return JSONResponse(namespace_list)
    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=e.status)


@app.put("/updatePriority")
async def update_priority(request: Request):
    data = await request.json()
    name = data.get("name", "")
    namespace = data.get("namespace", "default")
    priority = data.get("priority", 0)

    try:
        job = crd_client.get_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name,
        )

        job["spec"]["priority"] = priority

        crd_client.patch_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name,
            body=job,
        )
        return JSONResponse({"success": True, "status": 200})

    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return JSONResponse({"error": str(e)}, status_code=e.status)


# Get a listing of workloads in kueue
def fetch_jobs():
    listing = crd_client.list_namespaced_custom_object(
        group="kueue.x-k8s.io",
        version="v1beta1",
        namespace="default",
        plural="workloads",
    )

    return format_workloads(listing)


def format_workloads(listing: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not listing:
        return []

    res = []

    for job in listing["items"]:
        id = job["metadata"]["uid"]
        name = job["metadata"]["name"]
        created_at = job["metadata"]["creationTimestamp"]
        namespace = job["metadata"]["namespace"]
        localQueueName = job["spec"].get("queueName", "Unknown")
        priority = job["spec"]["priority"]
        active = job["spec"].get("active", 0)
        status = "ADMITTED" if "admission" in job.get("status", {}) else "PENDING"

        statusVal = 1 if "admission" in job.get("status", {}) else 0
        order = (statusVal * 10) + priority

        res.append(
            {
                "id": id,
                "name": name,
                "namespace": namespace,
                "localQueueName": localQueueName,
                "priority": priority,
                "status": status,
                "active": active,
                "created_at": created_at,
                "order": order,
            }
        )

    return res


app = socketio.ASGIApp(sio, app)
