from typing import List

import kubernetes

from konduktor import kube_client
from konduktor import logging as konduktor_logging

# node taint/label
NODE_HEALTH_LABEL = "trainy.konduktor.ai/faulty"

logger = konduktor_logging.get_logger(__name__)


def nccl_single_test(node: str, thresh: int = 400):
    """Runs NCCL test within a node. Tests NVLINK BW

    Args:
        node (str): k8s node name
        thresh (int, optional): minimum busbw to be considered healthy
        H100SXM should report 450GB/s max theoretically. Default 400

    """


def nccl_pair_test(nodeA: str, nodeB: str, thresh: int = 350):
    """Runs NCCL test between a pair of nodes. Tests
    internode bandwidth

    Args:
        nodeA (str): k8s node name
        nodeB (str): k8s node name
        thresh (int, optional): minimum busbw to be considered healthy
        ConnectX-7 cards have a theoretical max BW of 400GB/s
        Defaults to 350GB/s.
    """
    pass


def health_check():
    """Gathers nodes with label/taint `trainy.konduktor.ai/faulty=true:NoSchedule`
    and attempts to run NCCL test on them. Nodes that pass
    have their label/taint removed.
    """
    pass


def untaint(node_name: str):
    """Removes label/taint of `trainy.konduktor.ai/faulty=true:NoSchedule`

    Args:
        node (str): k8s node name
    """
    core_api = kube_client.core_api()
    node = core_api.read_node(
        name=node_name,
        _request_timeout=kube_client.API_TIMEOUT,
    )

    if node.spec.taints is not None:
        node.spec.taints = [
            taint for taint in node.spec.taints if taint.key != NODE_HEALTH_LABEL
        ]

    # Patch the node with the new taints
    core_api.patch_node(
        name=node_name,
        body=node,
        _request_timeout=kube_client.API_TIMEOUT,
    )

    logger.info(f"Node {node_name} taint removed.")


def taint(node_name: str):
    """Labels/Taints node with `trainy.konduktor.ai/faulty=true:NoSchedule`

    Args:
        node (str): k8s node name
    """
    core_api = kube_client.core_api()
    taint = kubernetes.client.V1Taint(
        key=NODE_HEALTH_LABEL,
        value="true",
        effect="NoSchedule",
    )
    node = core_api.read_node(
        name=node_name,
        _request_timeout=kube_client.API_TIMEOUT,
    )

    if node.spec.taints is None:
        node.spec.taints = []

    # duplicate taints are disallowed
    tainted = any(taint.key == NODE_HEALTH_LABEL for taint in node.spec.taints)
    if not tainted:
        node.spec.taints.append(taint)

    # Patch the node with the new taints
    core_api.patch_node(
        name=node_name,
        body=node,
        _request_timeout=kube_client.API_TIMEOUT,
    )

    logger.info(f"Node {node_name} tainted.")


def list_nodes() -> List[str]:
    """returns a list of k8s node names

    Returns:
        List[str]: List of k8s node names
    """
    nodes = kube_client.core_api().list_node()
    return [node.metadata.name for node in nodes.items]
