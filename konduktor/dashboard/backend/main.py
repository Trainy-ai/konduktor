import datetime
import time
from typing import Any, Dict, List

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
from kubernetes import client
from kubernetes.client.exceptions import ApiException

from konduktor.kube_client import batch_api, core_api, crd_api

app = Flask(__name__)

# Ensure CORS is configured correctly
cors = CORS(app, resources={r"/*": {"origins": "*"}})


# SocketIO configuration
socketio = SocketIO(app, cors_allowed_origins="*", ping_interval=25, ping_timeout=60)


# Use Kubernetes API clients
# Initialize BatchV1 and CoreV1 API (native kubernetes)
batch_client = batch_api()
core_client = core_api()
# Initialize Kueue API
crd_client = crd_api()

# Global variables
CLIENT_CONNECTED = False
FIRST_RUN = True
BACKGROUND_TASK_RUNNING = False
LOG_CHECKPOINT_TIME = None
SELECTED_NAMESPACES: list[str] = []
PROD_LOGS_URL = "http://loki.loki.svc.cluster.local:3100/loki/api/v1/query_range"
DEV_LOGS_URL = "http://localhost:3100/loki/api/v1/query_range"


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


def format_log_entry(entry: List[str], namespace: str) -> Dict[str, str]:
    """
    Formats a log entry and its corresponding namespace

    Args:
        entry (List[str]): A list of log entry strings to be formatted.
        namespace (str): The namespace to apply to each log entry.

    Returns:
        Dict[str, str]: an object with the following properties:
        timestamp, log (message), and namespace
    """
    timestamp_ns = entry[0]
    log_message = entry[1]
    timestamp_s = int(timestamp_ns) / 1e9
    dt = datetime.datetime.utcfromtimestamp(timestamp_s)
    human_readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")
    formatted_log = {
        "timestamp": human_readable_time,
        "log": log_message,
        "namespace": namespace,
    }
    return formatted_log


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
            print(f"Workload Name: {workload['metadata']['name']}")

    except ApiException as e:
        print(f"Failed to list workloads: {e}")


# for testing: prints jobs in native kubernetes kueue
def list_all_jobs():
    try:
        jobs = batch_client.list_job_for_all_namespaces(watch=False)  # Get all jobs

        if not jobs.items:
            print("No jobs found.")
        else:
            print("Jobs found:")
            for job in jobs.items:
                print(f"Name: {job.metadata.name}, Namespace: {job.metadata.namespace}")

    except ApiException as e:
        print(f"Failed to list jobs: {e}")


def get_logs(FIRST_RUN: bool, dev: bool) -> List[Dict[str, str]]:
    global LOG_CHECKPOINT_TIME

    # print(f'SELECTED NAMESPACES (GET_LOGS): {SELECTED_NAMESPACES}')

    # Use the selected namespaces in the query
    namespace_filter = (
        "|".join(SELECTED_NAMESPACES) if SELECTED_NAMESPACES else "default"
    )
    query = f'{{k8s_namespace_name=~"{namespace_filter}"}}'

    # print(f'QUERY (GET_LOGS): {query}')

    if FIRST_RUN:
        # Calculate how many nanoseconds to look back when first time looking at logs
        # (currently 1 hour)
        now = int(time.time() * 1e9)
        one_hour_ago = now - int(3600 * 1e9)
        start_time = str(one_hour_ago)
    else:
        # calculate new start_time based on newest, last message
        if LOG_CHECKPOINT_TIME is None:
            LOG_CHECKPOINT_TIME = 0
        start_time = str(int(LOG_CHECKPOINT_TIME) + 1)

    params = {"query": query, "start": start_time, "limit": "300"}

    url = DEV_LOGS_URL if dev else PROD_LOGS_URL
    response = requests.get(url, params=params)
    formatted_logs = []

    last = 0

    if response.status_code == 200:
        data = response.json()
        rows = data["data"]["result"]

        for row in rows:
            namespace = row["stream"]["k8s_namespace_name"]
            for value in row["values"]:
                last = max(int(value[0]), last)
                formatted_logs.append(format_log_entry(value, namespace))
        # print('status 200 getting logs')

    if formatted_logs:
        # sort because sometimes loki API is wrong and logs are out of order
        formatted_logs.sort(
            key=lambda log: datetime.datetime.strptime(
                log["timestamp"], "%Y-%m-%d %H:%M:%S"
            )
        )
        LOG_CHECKPOINT_TIME = last

    # print(f'formatted logs length: {len(formatted_logs)}')

    return formatted_logs


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
        print(f"Kueue Workload '{name}' deleted successfully.")

        """
        list_all_workloads()
        list_all_jobs()

        print(f"Native Kubernetes Job Name: {native_job_name}")

        batch_client.delete_namespaced_job(
            name=native_job_name,
            namespace=namespace,
            body=delete_options
        )
        print(f"Native Kubernetes Job {native_job_name} deleted successfully.")
        """

        return jsonify({"success": True, "status": 200})

    except ApiException as e:
        print(f"Exception: {e}")
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
        print(f"Exception: {e}")
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
        print(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status


# websocket connection for continuous log fetching


@socketio.on("connect")
def handle_connect():
    global CLIENT_CONNECTED, FIRST_RUN, BACKGROUND_TASK_RUNNING
    CLIENT_CONNECTED = True
    FIRST_RUN = True
    print("Client connected")

    # Start the background task only if it's not already running
    if not BACKGROUND_TASK_RUNNING:
        BACKGROUND_TASK_RUNNING = True
        socketio.start_background_task(send_logs)


def send_logs():
    global CLIENT_CONNECTED, FIRST_RUN, BACKGROUND_TASK_RUNNING
    while CLIENT_CONNECTED:
        logs = []
        try:
            # Attempt to get logs from the production setup; if fails, switch to dev
            logs = get_logs(FIRST_RUN, False)
        except Exception:
            logs = get_logs(FIRST_RUN, True)

        FIRST_RUN = False  # After the first successful fetch, set to False
        if logs:
            socketio.emit("log_data", logs)

        time.sleep(5)

    # Background task is no longer running after the loop
    BACKGROUND_TASK_RUNNING = False


@socketio.on("update_namespaces")
def handle_update_namespaces(namespaces):
    global SELECTED_NAMESPACES
    SELECTED_NAMESPACES = namespaces


@socketio.on("disconnect")
def handle_disconnect():
    global CLIENT_CONNECTED, FIRST_RUN
    CLIENT_CONNECTED = False
    FIRST_RUN = True
    print("Client disconnected")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
