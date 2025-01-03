"""Batch job execution via k8s jobsets
https://jobset.sigs.k8s.io/
https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/
"""

import pprint
import tempfile
from typing import Any, Dict, Optional

import konduktor
from konduktor import kube_client, logging
from konduktor.backends import backend
from konduktor.utils import common_utils, kubernetes_utils

Path = str
logger = logging.get_logger(__file__)

JOBSET_API_GROUP =  "jobset.x-k8s.io"
JOBSET_API_VERSION = "v1alpha2"
JOBSET_PLURAL = "jobsets"

def create_pod_spec(task: 'konduktor.Task') -> Dict[str, Any]:
    """Merges the task defintion with config
    to create a final pod spec dict for the job

    Returns:
        Dict[str, Any]: k8s pod spec
    """

    with tempfile.NamedTemporaryFile() as temp:
        # fill in the pod template with some of the
        if task.resources.accelerators:
            num_gpus = list(task.resources.accelerators.values())[0]
        else:
            num_gpus = None

        common_utils.fill_template(
            'pod.yaml.j2',
            {
                # TODO(asaiacai) need to parse/round these numbers and sanity check
                'cpu': kubernetes_utils.parse_cpu_or_gpu_resource(task.resources.cpus),
                'memory': kubernetes_utils.parse_memory_resource(task.resources.memory),
                'image_id': task.resources.image_id,
                'num_gpus': num_gpus,
                'job_name': task.name, # append timestamp and user id here?
                'run_cmd': task.run
            },
            temp.name
        )
        pod_config = common_utils.read_yaml(temp.name)

        # merge with `~/.konduktor/config.yaml``
        kubernetes_utils.combine_pod_config_fields(temp.name, pod_config)
        pod_config = common_utils.read_yaml(temp.name)

    # TODO(asaiacai): have some schema validations here
    return pod_config


def create_jobset(namespace: str, task: 'konduktor.Task', pod_spec: Dict[str, Any]):
    """Creates a jobset based on the task definition and pod spec
    """
    with tempfile.NamedTemporaryFile() as temp:
        common_utils.fill_template(
            'jobset.yaml.j2',
            {
                'job_name': task.name,
                'num_nodes': task.num_nodes,
                'user_id': common_utils.get_user_hash(),
                'timestamp': common_utils.get_timestamp(),
            },
            temp.name
        )
        jobset_spec = common_utils.read_yaml(temp.name)
    jobset_spec['jobset']['spec']['replicatedJobs'][0]['template']['spec']['template'] = pod_spec
    # TODO(asaiacai): set environment variables here
    try:
        response = kube_client.crd_api().create_namespaced_custom_object(
            group=JOBSET_API_GROUP,
            version=JOBSET_API_VERSION,
            namespace=namespace,
            plural=JOBSET_PLURAL,
            body=jobset_spec['jobset']
        )
        import pdb; pdb.set_trace()
        pprint(response)
    except kube_client.api_exception() as err:
        print(
            f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {err}"
        )

def list_jobset(namespace: str):
    """Lists all jobsets in this namespace
    """
    try:
        response = kube_client.crd_api().list_namespaced_custom_object(
            JOBSET_API_GROUP, JOBSET_API_VERSION, namespace, JOBSET_PLURAL
        )
        pprint(response)
    except kube_client.api_exception():
        print(
            f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {err}"
        )

def get_jobset(namespace: str, job_name: str):
    """Retrieves jobset in this namespace
    """
    try:
        response = kube_client.crd_api().get_namespaced_custom_object(
            JOBSET_API_GROUP,
            JOBSET_API_VERSION,
            namespace,
            JOBSET_PLURAL,
            job_name,
        )
        pprint(response)
    except kube_client.api_exception() as err:
        print(
            f"Exception when calling CustomObjectsApi->create_namespaced_custom_object: {err}"
        )


class JobsetBackend(backend.Backend):

    def _sync_file_mounts(
        self,
        all_file_mounts: Optional[Dict[Path, Path]],
        storage_mounts: Optional[Dict[Path, 'storage_lib.Storage']],
    ) -> None:
        #TODO: this needs to upload files to blob store
        logger.warning("i'm `_sync_file_mounts` of jobset backend. I'm not doing anything")
        pass
        # raise NotImplementedError

    def _execute(
        self,
        task: 'konduktor.Task',
        detach_run: bool,
        dryrun: bool = False) -> Optional[int]:
        """Executes the task on the cluster. By creating a jobset

        Returns:
            Job id if the task is submitted to the cluster, None otherwise.
        """

        if task.run is None:
            raise ValueError("run commands are empty")
        else:
            valid_resource = self.check_resources_fit_cluster(task)


        # first define the pod spec then create the jobset definition
        pod_spec = create_pod_spec(task)
        context = kube_client.get_current_kube_config_context_name()
        namespace = kube_client.get_kube_config_context_namespace(context)
        create_jobset(namespace, task, pod_spec['kubernetes']['pod_config'])


    def check_resources_fit_cluster(self, task: 'konduktor.Task') -> bool:
        """Check whether resources of the task are satisfied by clusterqueue.
        We return true if the maximum amount the request will be satisfied by the
        the resource quota in the Kueue clusterqueue assigned to the requested
        local queue.
        """
        #(asaiacai) TODO: might not even use this outside of checking kueue resource quotas
        logger.error("i'm just doing passthrough right now from `check_resources_fit_cluster`")
        return True
