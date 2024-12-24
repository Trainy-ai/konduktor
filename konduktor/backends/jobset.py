"""Batch job execution via k8s jobsets
https://jobset.sigs.k8s.io/
https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/
"""

import pprint
from typing import Dict, Optional

import konduktor
from konduktor.backends import backend
from konduktor import logging
from konduktor import kube_client

Path = str
logger = logging.get_logger(__file__)

JOBSET_API_GROUP =  "jobset.x-k8s.io"
JOBSET_API_VERSION = "v1alpha2"
JOBSET_PLURAL = "jobsets"

def create_jobset(namespace: str, task: 'konduktor.Task'):
    """Creates a jobset based on the task definition
    """
    try:
        response = kube_client.crd_api().create_namespaced_custom_object(
            JOBSET_API_GROUP,
            JOBSET_API_VERSION,
            namespace,
            JOBSET_PLURAL,
            jobset_example
        )
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
    except kube_client.api_exception() as e:
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
        logger.warning("i'm `_sync_file_mounts` of jobset backend. I'm not doing anything")
        pass
        # raise NotImplementedError

    def _execute(
        self,
        task: 'konduktor.Task',
        detach_run: bool,
        dryrun: bool = False) -> Optional[int]:
        """Executes the task on the cluster.

        Returns:
            Job id if the task is submitted to the cluster, None otherwise.
        """

        if task.run is None:
            raise ValueError("run commands are empty")
        else:
            valid_resource = self.check_resources_fit_cluster(task)

        
        # define the run script here (sky uses ray code gen)
        # here i define the jobset
        context = kube_client.get_current_kube_config_context_name()
        namespace = kube_client.get_kube_config_context_namespace(context)
        create_jobset(namespace, task)
        
        

    def check_resources_fit_cluster(self, task: 'konduktor.Task') -> bool:
        """Check whether resources of the task are satisfied by clusterqueue.
        We return true if the maximum amount the request will be satisfied by the
        the resource quota in the Kueue clusterqueue assigned to the requested
        local queue.
        """
        #(asaiacai) TODO
        logger.error("i'm just doing passthrough right now from `check_resources_fit_cluster`")
        return True
