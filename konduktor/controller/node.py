
import hashlib
import jinja2
import kubernetes
import time
from typing import Any, Dict, List, Tuple


from konduktor import kube_client
from konduktor import logging as konduktor_logging


NODE_HEALTH_LABEL = "trainy.konduktor.ai/faulty"
POD_DRAIN_GRACE_PERIOD = 1 # pod drain in seconds

logger = konduktor_logging.get_logger(__name__)


def nccl_single_test(node: str) -> float:
    """Runs NCCL test within a node. Tests NVLINK BW
    TODO(asaiacai): additional health checks for GPU
    https://github.com/imbue-ai/cluster-health/blob/master/gpu_stress_test/gpu_stress_test.py
    Args:
        node (str): k8s node name
        thresh (int, optional): minimum busbw to be considered healthy
        H100SXM should report 450GB/s max theoretically. Default 400
    Returns:
        float: measured busbw
    """
    hash = hashlib.md5(node.encode()).hexdigest()[-4:]



def nccl_pair_test(nodeA: str, nodeB: str, thresh: int = 350) -> float:
    """Runs NCCL test between a pair of nodes. Tests
    internode bandwidth

    Args:
        nodeA (str): k8s node name
        nodeB (str): k8s node name
        thresh (int, optional): minimum busbw to be considered healthy
        ConnectX-7 cards have a theoretical max BW of 400GB/s
        Defaults to 350GB/s.
    Returns:
        float: measured busbw
    """
    hash = hashlib.md5((nodeA + nodeB).encode()).hexdigest()[-4:]


def health_check() -> None:
    """Gathers nodes with label/taint `trainy.konduktor.ai/faulty=true:NoSchedule`
    and attempts to run health checks. Nodes that pass
    have their label/taint removed. Nodes that fail are cordoned. After the health
    check, there should be no tainted nodes, only cordoned and healthy nodes. Sys
    admins can further inspect cordoned nodes and reboot/power cycle them and have
    them rejoin the node pool.
    """
    
    tainted_nodes = list_nodes(tainted=True)
    logger.info(f"performing health check on tainted nodes:\n {tainted_nodes}")
    evaluated_nodes = set(tainted_nodes)
    failed_nodes = set()

    # First test NVLINK within every node
    nccl_test_results = []
    for node in tainted_nodes:
        drain_node(node)
        time.sleep(POD_DRAIN_GRACE_PERIOD) # give chance to drain pods
        nccl_test_results.append(nccl_single_test(node))

    # see if there was a single node failure
    for node, result in zip(tainted_nodes, nccl_test_results):
        if True: # TODO
            failed_nodes.append(node)

    for node in failed_nodes:
        tainted_nodes.remove(node)
    
    # Now from the good nodes, test the internode connectivity in a ring with pairwise NCCL. 
    # We're not testing all the nodes at the same time to isolate 
    # a single faulty node. A node is known to be faulty if it fails
    # between at least two separate hosts. Edge case when only one node for testing
    nccl_pairs: Dict[str, Tuple[Any, Any]] = {}
    if len(tainted_nodes) > 1:
        # [a, b] --> [b, a, b, a]
        tainted_nodes = tainted_nodes[-1] + tainted_nodes + tainted_nodes[0]
        n = len(tainted_nodes)
        for i in range(1, n - 1):
            testA = nccl_pair_test(tainted_nodes[i - 1], tainted_nodes[i])
            testB = nccl_pair_test(tainted_nodes[i], tainted_nodes[i + 1])
            nccl_pairs[tainted_nodes[i]] = (testA, testB)
    
    # read pairwise nccl test logs
    for node, (testA, testB) in nccl_pairs.items():
        if not (testA and testB):
            failed_nodes.add(node)

    
    for node in failed_nodes:
        logger.info(f"health check failed on {node}, cordoning")
        cordon_node(node)

    # cleanup taints
    for node in evaluated_nodes:
        untaint(node)


def cordon_node(node_name: str) -> None:
    core_api = kube_client.core_api()
    body = {
        "spec": {
            "unschedulable": True
        }
    }
    core_api.patch_node(
        name=node_name,
        body=body,
        _request_timeout=kube_client.API_TIMEOUT,
    )
    logger.info(f"Node {node_name} cordoned.")


def uncordon_node(node_name):
    core_api = kube_client.core_api()
    body = {
        "spec": {
            "unschedulable": False
        }
    }
    core_api.patch_node(
        name=node_name, 
        body=body,
        _request_timeout=kube_client.API_TIMEOUT
        )
    print(f"Node {node_name} uncordoned.")


def is_daemonset_pod(pod) -> bool:
    if pod.metadata.owner_references:
        for owner_reference in pod.metadata.owner_references:
            if owner_reference.kind == "DaemonSet":
                return True
    return False


def drain_node(node_name: str) -> None:
    # Get all pods on the node
    core_api = kube_client.core_api()
    pods = core_api.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name}").items

    # Delete the pods that are not part of DaemonSets
    for pod in pods:
        if is_daemonset_pod(pod):
            logger.info(f"Skipping DaemonSet pod {pod.metadata.name} from namespace {pod.metadata.namespace}")
            continue
        try:
            core_api.delete_namespaced_pod(
                name=pod.metadata.name, 
                namespace=pod.metadata.namespace,
                _request_timeout=kube_client.API_TIMEOUT
            )
            logger.info(f"Pod {pod.metadata.name} evicted from {node_name}.")
        except kube_client.api_exception() as e:
            logger.warning(f"Exception when evicting pod {pod.metadata.name}: {e}")


def untaint(node_name: str) -> None:
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


def taint(node_name: str) -> None:
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


def list_nodes(tainted: bool = False) -> List[str]:
    """returns a list of k8s node names
    Argss:
        tainted (bool): Only return tainted nodes.

    Returns:
        List[str]: List of k8s node names
    """
    nodes = kube_client.core_api().list_node()
    node_lst = []
    for node in nodes.items:
        if not tainted:
            node_lst.append(node.metadata.name)
        elif (tainted and node.spec.taints is not None
            and any(taint.key == NODE_HEALTH_LABEL for taint in node.spec.taints)):
            node_lst.append(node.metadata.name)
    return node_lst

if __name__ == "__main__":
    nccl_pair_test()