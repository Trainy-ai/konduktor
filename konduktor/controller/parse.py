import os
import re
from typing import Any, Dict, List

import requests

from konduktor import logging as konduktor_logging

# comma separated list of namespaces to watch for pod errors
WATCHED_NAMESPACES = os.environ.get("WATCHED_NAMESPACES", "default").split(",")
LOGS_SINCE = 10  # retrieves logs generated in the past 30 seconds
LOG_ENDPOINT = os.environ.get(
    "LOG_ENDPOINT",
    # this assumes you have access to this endpoint by
    # running as a deployment within the cluster
    # for local development use 'http://localhost:3100' and
    # kubectl port-forward svc/loki -n loki 3100:3100
    "http://loki.loki.svc.cluster.local:3100",
)
QUERY_URL = "/loki/api/v1/query_range"
# has to be either 'skypilot' or 'plain'
POD_LOG_TYPE = os.environ.get("POD_LOG_TYPE", "skypilot")

logger = konduktor_logging.init_logger(__name__)
logger.info(f"using POD_LOG_TYPE = {POD_LOG_TYPE}")


def _query_range(pattern: str, **label_filters) -> List[Dict[str, Any]]:
    """Send LogQL query_range to loki
    https://grafana.com/docs/loki/latest/reference/loki-http-api/#query-logs-within-a-range-of-time

    Args:
        pattern (str): regex pattern to match loglines against

    Returns:
        List[Dict[str, Any]]: List of loglines
    """
    url = f"{LOG_ENDPOINT}{QUERY_URL}"
    formatted_filters = ", ".join(
        f'{key}="{value}"' for key, value in label_filters.items()
    )
    query = r"{" f"{formatted_filters}" r"}" f"|~ {pattern}"
    params = {"query": query, "since": f"{LOGS_SINCE}s"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data["data"]["result"]
    elif response.status_code == 400:
        logger.error(f"Bad Request: {response.status_code}")
        logger.error(response.json())  # Optionally print the error details
    else:
        logger.error(f"loki query failed {params}")
    return []


class PodLogParser:
    """Base class for handling pod logs. A PodLogParser is responsible
    for turning raw queries from Loki into lists of degraded pods.
    """

    @classmethod
    def validate_logs(self, logs):
        """Reads pod logs and returns a list of nodes that had a pod
        error that indicated a GPU, CUDA, NCCL error

        Returns:
            List[str]: A list of node names with a detected failure from pod logs
        """
        raise NotImplementedError


class SkyLogParser(PodLogParser):
    @classmethod
    def check_logs(self, logs):
        pass


class PlainLogParser(PodLogParser):
    @classmethod
    def check_logs(self, logs) -> List[str]:
        # TODO: implement Pod log parsing
        return []


_pod_parser = {
    "skypilot": SkyLogParser,
    "plain": PlainLogParser,
}[POD_LOG_TYPE]


def pod_errors() -> List[str]:
    global _pod_parser
    logger.info("querying pod logs")
    return []


def sxid_error(pattern: str, log_content: str) -> int:
    """Regex pattern match for an xid error, from `log_content` otherwise return 0
    Example Xid error from dmesg
    [1235733.431527] NVRM: Xid (PCI:0000:4e:00): 79, pid='<unknown>', name=<unknown>, GPU has fallen off the bus.
    Example sxid error from dmesg
    [1235733.431527] nvidia-nvswitch3: SXid (PCI:0000:4e:00.0): 12028, Non-fatal, Link 32 egress non-posted PRIV error (First)
    """  # noqa: E501

    match = re.search(pattern, log_content)
    if match:
        return int(match.group(1))

    return 0


def is_dmesg_error(log_content: str) -> int:
    """Returns (S)Xid error code, zero otherwise"""
    return sxid_error(r"SXid.*?: (\d+),", log_content) or sxid_error(
        r"NVRM: Xid.*?: (\d+),", log_content
    )


def dmesg_errors() -> List[str]:
    logger.info("checking dmesg logs")
    pattern = r"`(?i)NVRM: xid` or `(?i)SXid` or `(?i)error`"
    log_lines = _query_range(pattern, k8s_daemonset_name="dmesg")
    bad_nodes = []
    for line in log_lines:
        log_node, log_content = line["stream"]["k8s_node_name"], line["values"][0][1]
        if is_dmesg_error(log_content):
            logger.info(f"node `{log_node}` has dmesg error: {log_content}")
            bad_nodes.append(log_node)
    return bad_nodes


if __name__ == "__main__":
    import time

    while True:
        time.sleep(5)
        print(dmesg_errors())
