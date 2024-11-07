import logging
import os
from typing import Any, Dict, List

from flask import Flask, jsonify, request
from flask_cors import CORS
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from konduktor.kube_client import batch_api, core_api, crd_api

from .sockets import socketio

# Configure the logger
logging.basicConfig(
    level=logging.DEBUG
    if os.environ.get("KONDUKTOR_DEBUG") in [None, "1"]
    else logging.INFO,
    format="%(asctime)s - %(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Ensure CORS is configured correctly
cors = CORS(app, resources={r"/*": {"origins": "*"}})

# Attach socketio to app after app is created
socketio.init_app(app, cors_allowed_origins="*")

# Use Kubernetes API clients
# Initialize BatchV1 and CoreV1 API (native kubernetes)
batch_client = batch_api()
core_client = core_api()
# Initialize Kueue API
crd_client = crd_api()


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
        # name = job["metadata"]["ownerReferences"][0]["name"]
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


"""
# for testing: prints workloads in kueue
def list_all_workloads(namespace="default"):
    try:
        # List workloads from the CRD API
        workloads = crd_client.list_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
        )
        for workload in workloads.get("items", []):
            logger.debug(f"Workload Name: {workload['metadata']['name']}")

    except ApiException as e:
        logger.debug(f"Failed to list workloads: {e}")


# for testing: prints jobs in native kubernetes kueue
def list_all_jobs():
    try:
        jobs = batch_client.list_job_for_all_namespaces(watch=False)  # Get all jobs

        if not jobs.items:
            logger.debug("No jobs found.")
        else:
            logger.debug("Jobs found:")
            for job in jobs.items:
                logger.debug(
                    f"Name: {job.metadata.name},
                    Namespace: {job.metadata.namespace}"
                )

    except ApiException as e:
        logger.debug(f"Failed to list jobs: {e}")
"""


# ROUTES


@app.route("/", methods=["GET"])
def home():
    return jsonify({"home": "/"})


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Pong from backend!"})


@app.route("/deleteJob", methods=["DELETE"])
def delete_job():
    data = request.get_json()
    name = data.get("name", "")
    namespace = data.get("namespace", "default")

    """
    # This is because kueue and native kubernetes have different job names:
    # Split the name into parts using the '-' delimiter
    name_parts = name.split('-')
    # Slice the list to get all elements except the first and the last
    native_job_name_parts = name_parts[1:-1]
    # Join the sliced parts back together with '-'
    native_job_name = '-'.join(native_job_name_parts)
    """

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

        """
        list_all_workloads()
        list_all_jobs()

        logger.debug(f"Native Kubernetes Job Name: {native_job_name}")

        batch_client.delete_namespaced_job(
            name=native_job_name,
            namespace=namespace,
            body=delete_options
        )
        logger.debug(f"Native Kubernetes Job {native_job_name} deleted successfully.")
        """

        return jsonify({"success": True, "status": 200})

    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status


@app.route("/getJobs", methods=["GET"])
def get_jobs():
    rows = fetch_jobs()
    return jsonify(rows)


@app.route("/getNamespaces", methods=["GET"])
def get_namespaces():
    try:
        # Get the list of namespaces
        namespaces = core_client.list_namespace()
        # Extract the namespace names from the response
        namespace_list = [ns.metadata.name for ns in namespaces.items]
        return jsonify(namespace_list)
    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status


@app.route("/updatePriority", methods=["PUT"])
def update_priority():
    data = request.get_json()
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
        return jsonify({"success": True, "status": 200})

    except ApiException as e:
        logger.debug(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
