# Proprietary Changes made for Trainy under the Trainy Software License
# Original source: skypilot: https://github.com/skypilot-org/skypilot
# which is Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Kubernetes utilities."""
import dataclasses
import functools
import json
import math
import os
import re
import typing
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import yaml

from konduktor import config, kube_client, logging
from konduktor.utils import common_utils, kubernetes_enums

if typing.TYPE_CHECKING:
    pass

DEFAULT_NAMESPACE = 'default'

DEFAULT_SERVICE_ACCOUNT_NAME = 'konduktor-service-account'

MEMORY_SIZE_UNITS = {
    'B': 1,
    'K': 2**10,
    'M': 2**20,
    'G': 2**30,
    'T': 2**40,
    'P': 2**50,
}

# The resource keys used by Kubernetes to track NVIDIA GPUs and Google on
# nodes. These keys are typically used in the node's status.allocatable
# or status.capacity fields to indicate the available resources on the node.
GPU_RESOURCE_KEY = 'nvidia.com/gpu'

NO_ACCELERATOR_HELP_MESSAGE = (
    'If your cluster contains GPUs, make sure '
    f'{GPU_RESOURCE_KEY} resource is available '
    'on the nodes and the node labels for identifying GPUs '
    '(e.g. `nvidia.com/gpu` are setup correctly. ')


logger = logging.get_logger(__name__)


class GPULabelFormatter:
    """Base class to define a GPU label formatter for a Kubernetes cluster

    A GPU label formatter is a class that defines how to use GPU type labels in
    a Kubernetes cluster. It is used by the Kubernetes cloud class to pick the
    key:value pair to use as node selector for GPU nodes.
    """

    @classmethod
    def get_label_key(cls, accelerator: Optional[str] = None) -> str:
        """Returns the label key for GPU type used by the Kubernetes cluster"""
        raise NotImplementedError

    @classmethod
    def get_label_keys(cls) -> List[str]:
        """Returns a list of label keys for GPU used by Kubernetes cluster."""
        raise NotImplementedError

    @classmethod
    def get_label_value(cls, accelerator: str) -> str:
        """Given a GPU type, returns the label value to be used"""
        raise NotImplementedError

    @classmethod
    def match_label_key(cls, label_key: str) -> bool:
        """Checks if the given label key matches the formatter's label keys"""
        raise NotImplementedError

    @classmethod
    def get_accelerator_from_label_value(cls, value: str) -> str:
        """Given a label value, returns the GPU type"""
        raise NotImplementedError

    @classmethod
    def validate_label_value(cls, value: str) -> Tuple[bool, str]:
        """Validates if the specified label value is correct.

        Used to check if the labelling on the cluster is correct and
        preemptively raise an error if it is not.

        Returns:
            bool: True if the label value is valid, False otherwise.
            str: Error message if the label value is invalid, None otherwise.
        """
        del value
        return True, ''


def get_gke_accelerator_name(accelerator: str) -> str:
    """Returns the accelerator name for GKE clusters.

    Uses the format - nvidia-tesla-<accelerator>.
    A100-80GB, H100-80GB, L4 are an exception. They use nvidia-<accelerator>.
    types are an exception as well keeping the given name.
    """
    if accelerator == 'H100':
        # H100 is named as H100-80GB in GKE.
        accelerator = 'H100-80GB'
    if accelerator in ('A100-80GB', 'L4', 'H100-80GB', 'H100-MEGA-80GB'):
        # A100-80GB, L4, H100-80GB and H100-MEGA-80GB
        # have a different name pattern.
        return 'nvidia-{}'.format(accelerator.lower())
    else:
        return 'nvidia-tesla-{}'.format(accelerator.lower())


class GKELabelFormatter(GPULabelFormatter):
    """GKE label formatter

    GKE nodes by default are populated with `cloud.google.com/gke-accelerator`
    label, which is used to identify the GPU type.
    """

    GPU_LABEL_KEY = 'cloud.google.com/gke-accelerator'
    ACCELERATOR_COUNT_LABEL_KEY = 'cloud.google.com/gke-accelerator-count'

    @classmethod
    def get_label_key(cls, accelerator: Optional[str] = None) -> str:
        return cls.GPU_LABEL_KEY

    @classmethod
    def get_label_keys(cls) -> List[str]:
        return [cls.GPU_LABEL_KEY]

    @classmethod
    def match_label_key(cls, label_key: str) -> bool:
        return label_key in cls.get_label_keys()

    @classmethod
    def get_label_value(cls, accelerator: str) -> str:
        return get_gke_accelerator_name(accelerator)

    @classmethod
    def get_accelerator_from_label_value(cls, value: str) -> str:
        if value.startswith('nvidia-tesla-'):
            return value.replace('nvidia-tesla-', '').upper()
        elif value.startswith('nvidia-'):
            acc = value.replace('nvidia-', '').upper()
            if acc == 'H100-80GB':
                # H100 can be either H100-80GB or H100-MEGA-80GB in GKE
                # we map H100 ---> H100-80GB and keep H100-MEGA-80GB
                # to distinguish between a3-high and a3-mega instances
                return 'H100'
            return acc
        else:
            raise ValueError(
                f'Invalid accelerator name in GKE cluster: {value}')


class GFDLabelFormatter(GPULabelFormatter):
    """GPU Feature Discovery label formatter

    NVIDIA GPUs nodes are labeled by GPU feature discovery
    e.g. nvidia.com/gpu.product=NVIDIA-H100-80GB-HBM3
    https://github.com/NVIDIA/gpu-feature-discovery

    GPU feature discovery is included as part of the
    NVIDIA GPU Operator:
    https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/overview.html

    This LabelFormatter can't be used in autoscaling clusters since accelerators
    may map to multiple label, so we're not implementing `get_label_value`
    """

    LABEL_KEY = 'nvidia.com/gpu.product'

    @classmethod
    def get_label_key(cls, accelerator: Optional[str] = None) -> str:
        return cls.LABEL_KEY

    @classmethod
    def get_label_keys(cls) -> List[str]:
        return [cls.LABEL_KEY]

    @classmethod
    def get_label_value(cls, accelerator: str) -> str:
        """An accelerator can map to many Nvidia GFD labels
        (e.g., A100-80GB-PCIE vs. A100-SXM4-80GB).
        As a result, we do not support get_label_value for GFDLabelFormatter."""
        raise NotImplementedError

    @classmethod
    def match_label_key(cls, label_key: str) -> bool:
        return label_key == cls.LABEL_KEY

    @classmethod
    def get_accelerator_from_label_value(cls, value: str) -> str:
        """Searches against a canonical list of NVIDIA GPUs and pattern
        matches the canonical GPU name against the GFD label.
        """
        canonical_gpu_names = [
            'A100-80GB', 'A100', 'A10G', 'H100', 'K80', 'M60', 'T4g', 'T4',
            'V100', 'A10', 'P4000', 'P100', 'P40', 'P4', 'L40', 'L4'
        ]
        for canonical_name in canonical_gpu_names:
            # A100-80G accelerator is A100-SXM-80GB or A100-PCIE-80GB
            if canonical_name == 'A100-80GB' and re.search(
                    r'A100.*-80GB', value):
                return canonical_name
            # Use word boundary matching to prevent substring matches
            elif re.search(rf'\b{re.escape(canonical_name)}\b', value):
                return canonical_name

        # If we didn't find a canonical name:
        # 1. remove 'NVIDIA-' (e.g., 'NVIDIA-RTX-A6000' -> 'RTX-A6000')
        # 2. remove 'GEFORCE-' (e.g., 'NVIDIA-GEFORCE-RTX-3070' -> 'RTX-3070')
        # 3. remove 'RTX-' (e.g. 'RTX-6000' -> 'RTX6000')
        return value.upper().replace('NVIDIA-',
                                     '').replace('GEFORCE-',
                                                 '').replace('RTX-', 'RTX')


# LABEL_FORMATTER_REGISTRY stores the label formats that will try to
# discover the accelerator type from. The order of the list is important, as
# it will be used to determine the priority of the label formats when
# auto-detecting the GPU label type.
LABEL_FORMATTER_REGISTRY = [
    GKELabelFormatter, GFDLabelFormatter
]

# Mapping of autoscaler type to label formatter
AUTOSCALER_TO_LABEL_FORMATTER = {
    kubernetes_enums.KubernetesAutoscalerType.GKE: GKELabelFormatter,
}


@functools.lru_cache()
def detect_gpu_label_formatter(
    context: Optional[str]
) -> Tuple[Optional[GPULabelFormatter], Dict[str, List[Tuple[str, str]]]]:
    """Detects the GPU label formatter for the Kubernetes cluster

    Returns:
        GPULabelFormatter: The GPU label formatter for the cluster, if found.
        Dict[str, List[Tuple[str, str]]]: A mapping of nodes and the list of
             labels on each node. E.g., {'node1': [('label1', 'value1')]}
    """
    # Get all labels across all nodes
    node_labels: Dict[str, List[Tuple[str, str]]] = {}
    nodes = get_kubernetes_nodes(context)
    for node in nodes:
        node_labels[node.metadata.name] = []
        for label, value in node.metadata.labels.items():
            node_labels[node.metadata.name].append((label, value))

    label_formatter = None

    # Check if the node labels contain any of the GPU label prefixes
    for lf in LABEL_FORMATTER_REGISTRY:
        for _, label_list in node_labels.items():
            for label, _ in label_list:
                if lf.match_label_key(label):
                    label_formatter = lf()
                    return label_formatter, node_labels

    return label_formatter, node_labels


@functools.lru_cache(maxsize=10)
def detect_accelerator_resource(
        context: Optional[str]) -> Tuple[bool, Set[str]]:
    """Checks if the Kubernetes cluster has GPU resource.

    Two types of accelerator resources are available which are each checked
    with nvidia.com/gpu. If nvidia.com/gpu resource is
    missing, that typically means that the Kubernetes cluster does not have
    GPUs or the nvidia GPU operator and/or device drivers are not installed.

    Returns:
        bool: True if the cluster has GPU_RESOURCE_KEY
            resource, False otherwise.
    """
    # Get the set of resources across all nodes
    cluster_resources: Set[str] = set()
    nodes = get_kubernetes_nodes(context)
    for node in nodes:
        cluster_resources.update(node.status.allocatable.keys())
    has_accelerator = (get_gpu_resource_key() in cluster_resources)

    return has_accelerator, cluster_resources


def check_credentials(context: Optional[str],
                      timeout: int = kube_client.API_TIMEOUT) -> \
        Tuple[bool, Optional[str]]:
    """Check if the credentials in kubeconfig file are valid

    Args:
        context (Optional[str]): The Kubernetes context to use. If none, uses
            in-cluster auth to check credentials, if available.
        timeout (int): Timeout in seconds for the test API call

    Returns:
        bool: True if credentials are valid, False otherwise
        str: Error message if credentials are invalid, None otherwise
    """
    try:
        namespace = get_kube_config_context_namespace(context)
        kubernetes.core_api(context).list_namespaced_pod(
            namespace, _request_timeout=timeout)
    except ImportError:
        return False, ('`kubernetes` package is not installed. '
                       'Install it with: pip install kubernetes')
    except kubernetes.api_exception() as e:
        # Check if the error is due to invalid credentials
        if e.status == 401:
            return False, 'Invalid credentials - do you have permission ' \
                          'to access the cluster?'
        else:
            return False, f'Failed to communicate with the cluster: {str(e)}'
    except kubernetes.config_exception() as e:
        return False, f'Invalid configuration file: {str(e)}'
    except kubernetes.max_retry_error():
        return False, ('Failed to communicate with the cluster - timeout. '
                       'Check if your cluster is running and your network '
                       'is stable.')
    except ValueError as e:
        return False, common_utils.format_exception(e)
    except Exception as e:  # pylint: disable=broad-except
        return False, ('An error occurred: '
                       f'{common_utils.format_exception(e, use_bracket=True)}')

    # If we reach here, the credentials are valid and Kubernetes cluster is up.
    # We now do softer checks to check if exec based auth is used and to
    # see if the cluster is GPU-enabled.

    _, exec_msg = is_kubeconfig_exec_auth(context)

    # We now check if GPUs are available and labels are set correctly on the
    # cluster, and if not we return hints that may help debug any issues.
    # This early check avoids later surprises for user when they try to run
    # `konduktor launch --gpus <gpu>` and the optimizer does not list Kubernetes as a
    # provider if their cluster GPUs are not setup correctly.
    gpu_msg = ''
    try:
        get_accelerator_label_key_value(context,
                                        acc_type='',
                                        acc_count=0,
                                        check_mode=True)
    except exceptions.ResourcesUnavailableError as e:
        # If GPUs are not available, we return cluster as enabled (since it can
        # be a CPU-only cluster) but we also return the exception message which
        # serves as a hint for how to enable GPU access.
        gpu_msg = str(e)
    if exec_msg and gpu_msg:
        return True, f'{gpu_msg}\n    Additionally, {exec_msg}'
    elif gpu_msg:
        return True, gpu_msg
    elif exec_msg:
        return True, exec_msg
    else:
        return True, None


def get_all_kube_context_names() -> List[str]:
    """Get all kubernetes context names available in the environment.

    Fetches context names from the kubeconfig file and in-cluster auth, if any.

    If running in-cluster and IN_CLUSTER_CONTEXT_NAME_ENV_VAR is not set,
    returns the default in-cluster kubernetes context name.

    We should not cache the result of this function as the admin policy may
    update the contexts.

    Returns:
        List[Optional[str]]: The list of kubernetes context names if
            available, an empty list otherwise.
    """
    k8s = kubernetes.kubernetes
    context_names = []
    try:
        all_contexts, _ = k8s.config.list_kube_config_contexts()
        # all_contexts will always have at least one context. If kubeconfig
        # does not have any contexts defined, it will raise ConfigException.
        context_names = [context['name'] for context in all_contexts]
    except k8s.config.config_exception.ConfigException:
        # If no config found, continue
        pass
    if is_incluster_config_available():
        context_names.append(kubernetes.in_cluster_context_name())
    return context_names


def parse_cpu_or_gpu_resource(resource_qty_str: str) -> Union[int, float]:
    resource_str = str(resource_qty_str)
    if resource_str[-1] == 'm':
        # For example, '500m' rounds up to 1.
        return math.ceil(int(resource_str[:-1]) / 1000)
    else:
        return float(resource_str)


def parse_memory_resource(resource_qty_str: str,
                          unit: str = 'B') -> Union[int, float]:
    """Returns memory size in chosen units given a resource quantity string."""
    if unit not in MEMORY_SIZE_UNITS:
        valid_units = ', '.join(MEMORY_SIZE_UNITS.keys())
        raise ValueError(
            f'Invalid unit: {unit}. Valid units are: {valid_units}')

    resource_str = str(resource_qty_str)
    bytes_value: Union[int, float]
    try:
        bytes_value = int(resource_str)
    except ValueError:
        memory_size = re.sub(r'([KMGTPB]+)', r' \1', resource_str)
        number, unit_index = [item.strip() for item in memory_size.split()]
        unit_index = unit_index[0]
        bytes_value = float(number) * MEMORY_SIZE_UNITS[unit_index]
    return bytes_value / MEMORY_SIZE_UNITS[unit]


def merge_dicts(source: Dict[Any, Any], destination: Dict[Any, Any]):
    """Merge two dictionaries into the destination dictionary.

    Updates nested dictionaries instead of replacing them.
    If a list is encountered, it will be appended to the destination list.

    An exception is when the key is 'containers', in which case the
    first container in the list will be fetched and merge_dict will be
    called on it with the first container in the destination list.
    """
    for key, value in source.items():
        if isinstance(value, dict) and key in destination:
            merge_dicts(value, destination[key])
        elif isinstance(value, list) and key in destination:
            assert isinstance(destination[key], list), \
                f'Expected {key} to be a list, found {destination[key]}'
            if key in ['containers', 'imagePullSecrets']:
                # If the key is 'containers' or 'imagePullSecrets, we take the
                # first and only container/secret in the list and merge it, as
                # we only support one container per pod.
                assert len(value) == 1, \
                    f'Expected only one container, found {value}'
                merge_dicts(value[0], destination[key][0])
            elif key in ['volumes', 'volumeMounts']:
                # If the key is 'volumes' or 'volumeMounts', we search for
                # item with the same name and merge it.
                for new_volume in value:
                    new_volume_name = new_volume.get('name')
                    if new_volume_name is not None:
                        destination_volume = next(
                            (v for v in destination[key]
                             if v.get('name') == new_volume_name), None)
                        if destination_volume is not None:
                            merge_dicts(new_volume, destination_volume)
                        else:
                            destination[key].append(new_volume)
            else:
                destination[key].extend(value)
        else:
            if destination is None:
                destination = {}
            destination[key] = value


def combine_pod_config_fields(
    cluster_yaml_path: str,
    cluster_config_overrides: Dict[str, Any],
) -> None:
    """Adds or updates fields in the YAML with fields from the ~/.konduktor/config's
    kubernetes.pod_spec dict.
    This can be used to add fields to the YAML that are not supported by
    yet, or require simple configuration (e.g., adding an
    imagePullSecrets field).
    Note that new fields are added and existing ones are updated. Nested fields
    are not completely replaced, instead their objects are merged. Similarly,
    if a list is encountered in the config, it will be appended to the
    destination list.
    For example, if the YAML has the following:
        ```
        ...
        node_config:
            spec:
                containers:
                    - name: ray
                    image: rayproject/ray:nightly
        ```
    and the config has the following:
        ```
        kubernetes:
            pod_config:
                spec:
                    imagePullSecrets:
                        - name: my-secret
        ```
    then the resulting YAML will be:
        ```
        ...
        node_config:
            spec:
                containers:
                    - name: ray
                    image: rayproject/ray:nightly
                imagePullSecrets:
                    - name: my-secret
        ```
    """
    with open(cluster_yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    yaml_obj = yaml.safe_load(yaml_content)
    # We don't use override_configs in `konduktor_config.get_nested`, as merging
    # the pod config requires special handling.
    kubernetes_config = config.get_nested(('kubernetes', 'pod_config'),
                                                   default_value={},
                                                   override_configs={})
    override_pod_config = (cluster_config_overrides.get('kubernetes', {}).get(
        'pod_config', {}))
    merge_dicts(override_pod_config, kubernetes_config)

    # Write the updated YAML back to the file
    common_utils.dump_yaml(cluster_yaml_path, yaml_obj)


def combine_metadata_fields(cluster_yaml_path: str) -> None:
    """Updates the metadata for all Kubernetes objects created with
    fields from the ~/.konduktor/config's kubernetes.custom_metadata dict.

    Obeys the same add or update semantics as combine_pod_config_fields().
    """

    with open(cluster_yaml_path, 'r', encoding='utf-8') as f:
        yaml_content = f.read()
    yaml_obj = yaml.safe_load(yaml_content)
    custom_metadata = konduktorpilot_config.get_nested(
        ('kubernetes', 'custom_metadata'), {})

    # List of objects in the cluster YAML to be updated
    combination_destinations = [
        # Service accounts
        yaml_obj['provider']['autoscaler_service_account']['metadata'],
        yaml_obj['provider']['autoscaler_role']['metadata'],
        yaml_obj['provider']['autoscaler_role_binding']['metadata'],
        yaml_obj['provider']['autoscaler_service_account']['metadata'],
        # Pod spec
        yaml_obj['available_node_types']['ray_head_default']['node_config']
        ['metadata'],
        # Services for pods
        *[svc['metadata'] for svc in yaml_obj['provider']['services']]
    ]

    for destination in combination_destinations:
        merge_dicts(custom_metadata, destination)

    # Write the updated YAML back to the file
    common_utils.dump_yaml(cluster_yaml_path, yaml_obj)


def merge_custom_metadata(original_metadata: Dict[str, Any]) -> None:
    """Merges original metadata with custom_metadata from config

    Merge is done in-place, so return is not required
    """
    custom_metadata = konduktorpilot_config.get_nested(
        ('kubernetes', 'custom_metadata'), {})
    merge_dicts(custom_metadata, original_metadata)


def check_nvidia_runtime_class(context: Optional[str] = None) -> bool:
    """Checks if the 'nvidia' RuntimeClass exists in the cluster"""
    # Fetch the list of available RuntimeClasses
    runtime_classes = kubernetes.node_api(context).list_runtime_class()

    # Check if 'nvidia' RuntimeClass exists
    nvidia_exists = any(
        rc.metadata.name == 'nvidia' for rc in runtime_classes.items)
    return nvidia_exists


def check_secret_exists(secret_name: str, namespace: str,
                        context: Optional[str]) -> bool:
    """Checks if a secret exists in a namespace

    Args:
        secret_name: Name of secret to check
        namespace: Namespace to check
    """

    try:
        kubernetes.core_api(context).read_namespaced_secret(
            secret_name, namespace, _request_timeout=kubernetes.API_TIMEOUT)
    except kubernetes.api_exception() as e:
        if e.status == 404:
            return False
        raise
    else:
        return True


def create_namespace(namespace: str, context: Optional[str]) -> None:
    """Creates a namespace in the cluster.

    If the namespace already exists, logs a message and does nothing.

    Args:
        namespace: Name of the namespace to create
        context: Name of the context to use. Can be none to use default context.
    """
    kubernetes_client = kubernetes.kubernetes.client
    try:
        kubernetes.core_api(context).read_namespace(namespace)
    except kubernetes.api_exception() as e:
        if e.status != 404:
            raise
    else:
        return

    ns_metadata = dict(name=namespace, labels={'parent': 'konduktorpilot'})
    merge_custom_metadata(ns_metadata)
    namespace_obj = kubernetes_client.V1Namespace(metadata=ns_metadata)
    try:
        kubernetes.core_api(context).create_namespace(namespace_obj)
    except kubernetes.api_exception() as e:
        if e.status == 409:
            logger.info(f'Namespace {namespace} already exists in the cluster.')
        else:
            raise


def get_autoscaler_type(
) -> Optional[kubernetes_enums.KubernetesAutoscalerType]:
    """Returns the autoscaler type by reading from config"""
    autoscaler_type = konduktorpilot_config.get_nested(('kubernetes', 'autoscaler'),
                                                 None)
    if autoscaler_type is not None:
        autoscaler_type = kubernetes_enums.KubernetesAutoscalerType(
            autoscaler_type)
    return autoscaler_type


def dict_to_k8s_object(object_dict: Dict[str, Any], object_type: 'str') -> Any:
    """Converts a dictionary to a Kubernetes object.

    Useful for comparing two Kubernetes objects. Adapted from
    https://github.com/kubernetes-client/python/issues/977#issuecomment-592030030

    Args:
        object_dict: Dictionary representing the Kubernetes object
        object_type: Type of the Kubernetes object. E.g., 'V1Pod', 'V1Service'.
    """

    class FakeKubeResponse:

        def __init__(self, obj):
            self.data = json.dumps(obj)

    fake_kube_response = FakeKubeResponse(object_dict)
    return kubernetes.api_client().deserialize(fake_kube_response, object_type)

#TODO(asaiacai): some checks here for CRDs for jobset and Kueue CRDs, queues, etc.


@dataclasses.dataclass
class KubernetesNodeInfo:
    """Dataclass to store Kubernetes node information."""
    name: str
    accelerator_type: Optional[str]
    # Resources available on the node. E.g., {'nvidia.com/gpu': '2'}
    total: Dict[str, int]
    free: Dict[str, int]


def get_kubernetes_node_info(
        context: Optional[str] = None) -> Dict[str, KubernetesNodeInfo]:
    """Gets the resource information for all the nodes in the cluster.

    Currently only GPU resources are supported. The function returns the total
    number of GPUs available on the node and the number of free GPUs on the
    node.

    If the user does not have sufficient permissions to list pods in all
    namespaces, the function will return free GPUs as -1.

    Returns:
        Dict[str, KubernetesNodeInfo]: Dictionary containing the node name as
            key and the KubernetesNodeInfo object as value
    """
    nodes = get_kubernetes_nodes(context)
    # Get the pods to get the real-time resource usage
    try:
        pods = get_all_pods_in_kubernetes_cluster(context)
    except kubernetes.api_exception() as e:
        if e.status == 403:
            pods = None
        else:
            raise

    lf, _ = detect_gpu_label_formatter(context)
    if not lf:
        label_key = None
    else:
        label_keys = lf.get_label_keys()

    node_info_dict: Dict[str, KubernetesNodeInfo] = {}

    for label_key in label_keys:
        for node in nodes:
            allocated_qty = 0
            if lf is not None and label_key in node.metadata.labels:
                accelerator_name = lf.get_accelerator_from_label_value(
                    node.metadata.labels.get(label_key))
            else:
                accelerator_name = None

            accelerator_count = get_node_accelerator_count(
                node.status.allocatable)

            if pods is None:
                accelerators_available = -1

            else:
                for pod in pods:
                    # Get all the pods running on the node
                    if (pod.spec.node_name == node.metadata.name and
                            pod.status.phase in ['Running', 'Pending']):
                        # Iterate over all the containers in the pod and sum the
                        # GPU requests
                        for container in pod.spec.containers:
                            if container.resources.requests:
                                allocated_qty += get_node_accelerator_count(
                                    container.resources.requests)

                accelerators_available = accelerator_count - allocated_qty

            node_info_dict[node.metadata.name] = KubernetesNodeInfo(
                name=node.metadata.name,
                accelerator_type=accelerator_name,
                total={'accelerator_count': int(accelerator_count)},
                free={'accelerators_available': int(accelerators_available)})

    return node_info_dict


def to_label_selector(tags):
    label_selector = ''
    for k, v in tags.items():
        if label_selector != '':
            label_selector += ','
        label_selector += '{}={}'.format(k, v)
    return label_selector


def get_namespace_from_config(provider_config: Dict[str, Any]) -> str:
    context = get_context_from_config(provider_config)
    return provider_config.get('namespace',
                               get_kube_config_context_namespace(context))


def get_context_from_config(provider_config: Dict[str, Any]) -> Optional[str]:
    context = provider_config.get('context',
                                  get_current_kube_config_context_name())
    if context == kubernetes.in_cluster_context_name():
        # If the context (also used as the region) is in-cluster, we need to
        # we need to use in-cluster auth by setting the context to None.
        context = None
    return context


def get_gpu_resource_key():
    """Get the GPU resource name to use in kubernetes.
    The function first checks for an environment variable.
    If defined, it uses its value; otherwise, it returns the default value.
    Args:
        name (str): Default GPU resource name, default is "nvidia.com/gpu".
    Returns:
        str: The selected GPU resource name.
    """
    # Retrieve GPU resource name from environment variable, if set.
    # Else use default.
    # E.g., can be nvidia.com/gpu-h100, amd.com/gpu etc.
    return os.getenv('CUSTOM_GPU_RESOURCE_KEY', default=GPU_RESOURCE_KEY)
