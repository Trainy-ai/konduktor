"""Batch job execution via k8s jobsets
https://jobset.sigs.k8s.io/
https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/
"""

import json
import pprint
import tempfile
from typing import Any, Dict, Optional

import konduktor
from konduktor import config, kube_client, logging
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

    # fill out the templating variables
    if task.resources.accelerators:
        num_gpus = list(task.resources.accelerators.values())[0]
    else:
        num_gpus = 0
    task.name = f"{task.name}-{common_utils.get_usage_run_id()[:4]}"
    node_hostnames = ",".join([f"{task.name}-workers-0-{idx}.{task.name}" for idx in range(task.num_nodes)])
    master_addr = f"{task.name}-workers-0-0.{task.name}"

    with tempfile.NamedTemporaryFile() as temp:
        common_utils.fill_template(
            'pod.yaml.j2',
            {
                # TODO(asaiacai) need to parse/round these numbers and sanity check
                'cpu': kubernetes_utils.parse_cpu_or_gpu_resource(task.resources.cpus),
                'memory': kubernetes_utils.parse_memory_resource(task.resources.memory),
                'image_id': task.resources.image_id,
                'num_gpus': num_gpus,
                'master_addr': master_addr,
                'num_nodes': task.num_nodes,
                'job_name': task.name, # append timestamp and user id here?
                'run_cmd': task.run,
                'node_hostnames': node_hostnames,
            },
            temp.name
        )
        pod_config = common_utils.read_yaml(temp.name)

        # merge with `~/.konduktor/config.yaml``
        kubernetes_utils.combine_pod_config_fields(temp.name, pod_config)
        pod_config = common_utils.read_yaml(temp.name)

    # TODO(asaiacai): have some schema validations. see
    # https://github.com/skypilot-org/skypilot/pull/4466

    return pod_config


def create_jobset(namespace: str, task: 'konduktor.Task', pod_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a jobset based on the task definition and pod spec
    and returns the created jobset spec
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
    # try:
    jobset = kube_client.crd_api().create_namespaced_custom_object(
        group=JOBSET_API_GROUP,
        version=JOBSET_API_VERSION,
        namespace=namespace,
        plural=JOBSET_PLURAL,
        body=jobset_spec['jobset']
    )
    logger.info(f"Created job {task.name}")
    return jobset
    # except kube_client.api_exception() as err:
    #     try:
    #         error_body = json.loads(err.body)
    #         error_message = error_body.get('message', '')
    #     except json.JSONDecodeError:
    #         error_message = str(e.body)
    #     else:
    #         # Re-raise the exception if it's a different error
    #         raise err

def list_jobset(namespace: str):
    """Lists all jobsets in this namespace
    """
    try:
        response = kube_client.crd_api().list_namespaced_custom_object(
            JOBSET_API_GROUP, JOBSET_API_VERSION, namespace, JOBSET_PLURAL
        )
        pprint(response)
    except kube_client.api_exception() as err:
        try:
            error_body = json.loads(e.body)
            error_message = error_body.get('message', '')
        except json.JSONDecodeError:
            error_message = str(e.body)
        else:
            # Re-raise the exception if it's a different error
            raise err

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
        try:
            error_body = json.loads(e.body)
            error_message = error_body.get('message', '')
        except json.JSONDecodeError:
            error_message = str(e.body)
        else:
            # Re-raise the exception if it's a different error
            raise err


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
        detach_run: bool = False,
        dryrun: bool = False) -> Optional[int]:
        """Executes the task on the cluster. By creating a jobset

        Returns:
            Job id if the task is submitted to the cluster, None otherwise.
        """

        if task.run is None:
            raise ValueError("run commands are empty")
        
        if task.name is None:
            raise ValueErorr("no name for the task was specified. You must specify a name for this task")


        # first define the pod spec then create the jobset definition
        pod_spec = create_pod_spec(task)
        context = kube_client.get_current_kube_config_context_name()
        namespace = kube_client.get_kube_config_context_namespace(context)
        create_jobset(namespace, task, pod_spec['kubernetes']['pod_config'])

        if not detach_run:
            # wait for job state to be up
            pass

            # stream logs from loki



