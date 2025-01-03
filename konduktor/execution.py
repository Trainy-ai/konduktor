"""Execution layer.

See `Stage` for a Task's life cycle.
"""
import enum
from typing import List, Optional

from konduktor import logging as konduktor_logging
from konduktor.backends import JobsetBackend
from konduktor.utils import ux_utils

logger = konduktor_logging.get_logger(__name__)


class Stage(enum.Enum):
    """Stages for a run of a konduktor.Task."""
    SYNC = enum.auto() # sync files to blob and creds to sharefs
    PENDING = enum.auto() # job pending scheduling
    EXEC = enum.auto() # job running
    COMPLETED = enum.auto() # job completed


def _execute(
    task: 'konduktor.Task',
    dryrun: bool = False,
    stream_logs: bool = True,
    stages: Optional[List[Stage]] = None,
    cluster_name: Optional[str] = None,
    detach_run: bool = False,
) -> Optional[str]:
    """Execute an task.

    Args:
      task: konduktor.Task
      dryrun: bool; if True, only print the provision info (e.g., cluster
        yaml).
      stream_logs: bool; whether to stream all tasks' outputs to the client.
      cluster_name: Name of the cluster to create/reuse.  If None,
        auto-generate a name.

    Returns:
      workload_id: Optional[int]; the job ID of the submitted job. None if the
        backend is not CloudVmRayBackend, or no job is submitted to
        the cluster.
    """
    # (asaiacai): in the future we may support more backends but not likely
    backend = JobsetBackend()

    if dryrun:
      logger.info('Dryrun finished.')
      return None, None

    # (asaiacai) should provisioning go somewhere around here?
    do_workdir = (Stage.SYNC in stages and not dryrun and
                    task.workdir is not None)
    do_file_mounts = (Stage.SYNC in stages and not dryrun and
                        (task.file_mounts is not None or
                        task.storage_mounts is not None))
    if do_workdir or do_file_mounts:
        logger.info(ux_utils.starting_message('Mounting files.'))

    if do_workdir:
        backend.sync_workdir(task.workdir)

    if do_file_mounts:
        backend.sync_file_mounts(task.file_mounts,
                                    task.storage_mounts)

    if Stage.EXEC in stages:
        job_id = backend.execute(task,
                                detach_run,
                                dryrun=dryrun)

    # attach to head node output if detach_run is False


    # implement JobsetBackend
    # sync_workdir
    # sync_file_mounts
    # execute
    return job_id


def launch(
    task: 'konduktor.Task',
    cluster_name: str,
    dryrun: bool = False,
    stream_logs: bool = True,
    detach_run: bool = False,
) -> Optional[int]:
    """Launch a task 

    Args:
        task: konduktor.Task
        name: str name of the task
        dryrun: if True, do not actually launch the task.
        stream_logs: if True, show the logs in the terminal.
        detach_run: If True, as soon as a job is submitted, return from this
            function and do not stream execution logs.

    Example:
        .. code-block:: python

            import konduktor
            task = konduktor.Task(run='echo hello konduktor')
            konduktor.launch(task)

    Raises:
      Other exceptions may be raised depending on the backend.

    Returns:
      workload_id: Optional[int]; the job ID of the submitted job.
    """

    stages = [
      Stage.SYNC,
      Stage.PENDING,
      Stage.EXEC,
      Stage.COMPLETED,
    ]

    return _execute(
        task=task,
        dryrun=dryrun,
        stream_logs=stream_logs,
        stages=stages,
        cluster_name=cluster_name,
        detach_run=detach_run,
    )
