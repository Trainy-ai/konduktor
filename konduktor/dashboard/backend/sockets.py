import asyncio
import datetime
import os
import time
from typing import Dict, List

import requests
from socketio import AsyncServer  # Import the AsyncServer for ASGI compatibility

from konduktor import logging as konduktor_logging

# SocketIO configuration
socketio = AsyncServer(
    cors_allowed_origins="*", ping_interval=25, ping_timeout=60, async_mode="asgi"
)

logger = konduktor_logging.get_logger(__name__)

# Global variables
CLIENT_CONNECTED = False
FIRST_RUN = True
BACKGROUND_TASK_RUNNING = False
LOG_CHECKPOINT_TIME = None
SELECTED_NAMESPACES: list[str] = []

# "http://loki.loki.svc.cluster.local:3100/loki/api/v1/query_range" for prod
# "http://localhost:3100/loki/api/v1/query_range" for local
LOGS_URL = os.environ.get("LOGS_URL", "http://localhost:3100/loki/api/v1/query_range")


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


def get_logs(FIRST_RUN: bool) -> List[Dict[str, str]]:
    global LOG_CHECKPOINT_TIME

    logger.debug(f"Selected namespaces: {SELECTED_NAMESPACES}")

    # Use the selected namespaces in the query
    namespace_filter = (
        "|".join(SELECTED_NAMESPACES) if SELECTED_NAMESPACES else "default"
    )
    query = f'{{k8s_namespace_name=~"{namespace_filter}"}}'

    logger.debug(f"Loki logs query: {query}")

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

    url = LOGS_URL
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

    if formatted_logs:
        # sort because sometimes loki API is wrong and logs are out of order
        formatted_logs.sort(
            key=lambda log: datetime.datetime.strptime(
                log["timestamp"], "%Y-%m-%d %H:%M:%S"
            )
        )
        LOG_CHECKPOINT_TIME = last

    logger.debug(f"Formatted logs length: {len(formatted_logs)}")

    return formatted_logs


async def send_logs():
    global CLIENT_CONNECTED, FIRST_RUN, BACKGROUND_TASK_RUNNING
    while CLIENT_CONNECTED:
        logs = get_logs(FIRST_RUN)

        FIRST_RUN = False  # After the first successful fetch, set to False
        if logs:
            await socketio.emit("log_data", logs)

        await asyncio.sleep(5)

    # Background task is no longer running after the loop
    BACKGROUND_TASK_RUNNING = False


@socketio.event
async def connect(sid, environ):
    global CLIENT_CONNECTED, FIRST_RUN, BACKGROUND_TASK_RUNNING
    CLIENT_CONNECTED = True
    FIRST_RUN = True
    logger.debug("Client connected")

    # Start the background task only if it's not already running
    if not BACKGROUND_TASK_RUNNING:
        BACKGROUND_TASK_RUNNING = True
        socketio.start_background_task(send_logs)


@socketio.event
async def update_namespaces(sid, namespaces):
    global SELECTED_NAMESPACES
    SELECTED_NAMESPACES = namespaces
    logger.debug("Updated namespaces")


@socketio.event
async def disconnect(sid):
    global CLIENT_CONNECTED, FIRST_RUN, BACKGROUND_TASK_RUNNING
    CLIENT_CONNECTED = False
    FIRST_RUN = True
    BACKGROUND_TASK_RUNNING = False
    logger.debug("Client disconnected")
