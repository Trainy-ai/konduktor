from flask import request, jsonify
from config import app


import argparse
from kubernetes import config, client
from kubernetes.client.exceptions import ApiException

import json
import os
import requests
import datetime

# Jobs stuff
# Make sure your cluster is running!
config.load_kube_config()
# Initialize Kueue API
crd_api = client.CustomObjectsApi()
# Initialize BatchV1 API (native)
batch_api = client.BatchV1Api()





def get_parser():
    parser = argparse.ArgumentParser(
        description="Interact with Queues e",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--namespace",
        help="namespace to list for",
        default="default",
    )
    return parser


def fetch_jobs():
    """
    Get a listing of jobs in the CLUSTER queue
    """

    listing = crd_api.list_namespaced_custom_object(
        group="kueue.x-k8s.io",
        version="v1beta1",
        namespace="default",
        plural="workloads",
    )

    return format_workloads(listing)

    # OLD
    listing = crd_api.list_namespaced_custom_object(
        group="batch",
        version="v1",
        namespace=args.namespace,
        plural="jobs",
    )

    return format_jobs(listing)

# NEW
def format_workloads(listing):
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
    
        res.append({
            "id": id,
            "name": name,
            "namespace": namespace,
            "localQueueName": localQueueName,
            "priority": priority,
            "status": status,
            "active": active,
            "created_at": created_at,
            "order": order
        })

    return res

# OLD
def get_cluster_status(job):
    conditions = job.get("status", {}).get("conditions", [])
    succeeded = job.get("status", {}).get("succeeded", 0)
    failed = job.get("status", {}).get("failed", 0)
    active = job.get("status", {}).get("active", 0)

    for condition in conditions:
        if condition["type"] == "Complete" and condition["status"] == "True":
            return "Completed"
        elif condition["type"] == "Failed" and condition["status"] == "True":
            return "Failed"
        elif condition["type"] == "Suspended" and condition["status"] == "True":
            return "Suspended"

    if active > 0:
        return "Running"

    if succeeded == 0 and failed == 0:
        return "In Progress"

    return "Unknown"
    
# OLD
def format_jobs(listing):
    if not listing:
        return []
    
    res = []
    
    for job in listing["items"]:

        # status = job.get("status", {})
        # print(json.dumps(status, indent=2))

        id = job["metadata"]["uid"]
        name = job["metadata"]["name"]
        created_at = job["metadata"]["creationTimestamp"]

        # Determine the status of the job
        status = get_cluster_status(job)
        
        # Total jobs (this example assumes `spec.completions` is the total)
        total_jobs = job.get("spec", {}).get("completions", 0)
        
        # Active jobs (assuming active jobs are inferred from conditions, if `status.succeeded` is not available)
        active_jobs = job.get("status", {}).get("active", 0)
        
        # Successful jobs
        successful_jobs = job.get("status", {}).get("succeeded", 0)
        
        # Failed jobs (if `status.failed` is available, use it; otherwise, assume failed if not succeeded)
        failed_jobs = job.get("status", {}).get("failed", 0)
        
        # Created by (assuming creator information might be in labels or annotations, example uses a placeholder)
        created_by = job["metadata"]["labels"].get("creator", "") if "labels" in job["metadata"] else "Unknown"

        res.append({
            "id": id,
            "name": name,
            "cluster_status": status,
            "total_jobs": total_jobs,
            "active": active_jobs,
            "successful": successful_jobs,
            "failed": failed_jobs,
            "created_at": created_at,
            "created_by": created_by
        })

    return res

def format_log_entry(entry):
    timestamp_ns = entry[0]
    log_message = entry[1]
    timestamp_s = int(timestamp_ns) / 1e9
    dt = datetime.datetime.utcfromtimestamp(timestamp_s)
    human_readable_time = dt.strftime('%Y-%m-%d %H:%M:%S')
    formatted_log = {
        "timestamp": human_readable_time,
        "log": log_message
    }
    return formatted_log








@app.route("/", methods=["GET"])
def home():
    return jsonify({"home": "/"})

@app.route("/jobs", methods=["GET"])
def get_jobs():

    rows = fetch_jobs()

    return jsonify(rows)

@app.route("/updatePriority", methods=["PUT"])
def update_priority():
    data = request.get_json()
    name = data.get('name', "")
    namespace = data.get('namespace', "default")
    priority = data.get('priority', 0)

    # TODO: Input validation

    try:

        job = crd_api.get_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name
        )

        job['spec']['priority'] = priority

        crd_api.patch_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name,
            body=job
        )
        return jsonify({'success': True, 'status': 200})

    except ApiException as e:
        print(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status
    
@app.route("/deleteJob", methods=["DELETE"])
def delete_job():
    data = request.get_json()
    name = data.get('name', "")
    namespace = data.get('namespace', "default")

    # This is because kueue and native kubernetes have different job names:
    # Split the name into parts using the '-' delimiter
    name_parts = name.split('-')
    # Slice the list to get all elements except the first and the last
    native_job_name_parts = name_parts[1:-1]
    # Join the sliced parts back together with '-'
    native_job_name = '-'.join(native_job_name_parts)

    # TODO: Input validation

    try:
        delete_options = client.V1DeleteOptions()

        batch_api.delete_namespaced_job(
            name=native_job_name,
            namespace=namespace,
            body=delete_options
        )
        print(f"Native Kubernetes Job {native_job_name} deleted successfully.")

        crd_api.delete_namespaced_custom_object(
            group="kueue.x-k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="workloads",
            name=name
        )
        print(f"Kueue Workload '{name}' deleted successfully.")

        return jsonify({'success': True, 'status': 200})

    except ApiException as e:
        print(f"Exception: {e}")
        return jsonify({"error": str(e)}), e.status

# TODO: websocket connection for continuous log fetching

@app.route("/logs", methods=["GET"])
def get_logs():

    url = "http://localhost:3100/loki/api/v1/query_range"

    rows = []

    # TODO: default namespace???
    query = '{k8s_namespace_name="loki"}'

    params = {
        'query': query,
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        rows = data["data"]["result"]

    formatted_logs = []
    for row in rows:
        for value in row["values"]:
            formatted_logs.append(format_log_entry(value))

    return jsonify(formatted_logs)

if __name__ == "__main__":
    app.run(debug=True)