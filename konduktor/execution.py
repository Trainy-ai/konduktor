"""Execution layer.

See `Stage` for a Task's life cycle.
"""
import enum
from typing import List, Optional, Tuple, Union

import colorama
logger = konduktor_logging.init_logger(__name__)


class Stage(enum.Enum):
    """Stages for a run of a konduktor.Task."""
    # TODO: rename actual methods to be consistent.
    PENDING = enum.auto()
    RUN = enum.auto()
    COMPLETED = enum.auto()
    FAILED = enum.auto()


def _execute(
    entrypoint: 'konduktor.Task',
    dryrun: bool = False,
    down: bool = False,
    stream_logs: bool = True,
    handle: Optional[backends.ResourceHandle] = None,
    stages: Optional[List[Stage]] = None,
    job_name: Optional[str] = None,
    detach: bool = False,
    detach_setup: bool = False,
    detach_run: bool = False,
) -> Tuple[Optional[str], Optional[backends.ResourceHandle]]:
    """Execute an entrypoint.

    If konduktor.Task is given

    Args:
      entrypoint: konduktor.Task
      dryrun: bool; if True, only print the provision info (e.g., cluster
        yaml).
      stream_logs: bool; whether to stream all tasks' outputs to the client.
      handle: Optional[backends.ResourceHandle]; if provided, execution will use
        an existing backend cluster handle instead of provisioning a new one.
      cluster_name: Name of the cluster to create/reuse.  If None,
        auto-generate a name.

    Returns:
      workload_id: Optional[int]; the job ID of the submitted job. None if the
        backend is not CloudVmRayBackend, or no job is submitted to
        the cluster.
      handle: Optional[backends.ResourceHandle]; the handle to the cluster. None
        if dryrun.
    """

    

@timeline.event
@usage_lib.entrypoint
def launch(
    task: Union['konduktor.Task'],
    cluster_name: Optional[str] = None,
    dryrun: bool = False,
    down: bool = False,
    stream_logs: bool = True,
    detach_setup: bool = False,
    detach_run: bool = False,
    no_setup: bool = False,
    clone_disk_from: Optional[str] = None,
) -> Tuple[Optional[int], Optional[backends.ResourceHandle]]:
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Launch a task 

    Args:
        task: konduktor.Task
        cluster_name: name of the cluster to create/reuse.  If None,
            auto-generate a name.
        retry_until_up: whether to retry launching the cluster until it is
            up.
        down: Tear down the cluster after all jobs finish (successfully or
            abnormally). If --idle-minutes-to-autostop is also set, the
            cluster will be torn down after the specified idle time.
            Note that if errors occur during provisioning/data syncing/setting
            up, the cluster will not be torn down for debugging purposes.
        dryrun: if True, do not actually launch the cluster.
        stream_logs: if True, show the logs in the terminal.
        optimize_target: target to optimize for. Choices: OptimizeTarget.COST,
            OptimizeTarget.TIME.
        detach_setup: If True, run setup in non-interactive mode as part of the
            job itself. You can safely ctrl-c to detach from logging, and it
            will not interrupt the setup process. To see the logs again after
            detaching, use `konduktor logs`. To cancel setup, cancel the job via
            `konduktor cancel`. Useful for long-running setup
            commands.
        detach_run: If True, as soon as a job is submitted, return from this
            function and do not stream execution logs.

    Example:
        .. code-block:: python

            import konduktor
            task = konduktor.Task(run='echo hello konduktor')
            konduktor.launch(task, cluster_name='my-cluster')

    Raises:
      Other exceptions may be raised depending on the backend.

    Returns:
      workload_id: Optional[int]; the job ID of the submitted job.
      handle: Optional[backends.ResourceHandle]; the handle to the cluster. None
        if dryrun.
    """
    entrypoint = task
    if not _disable_controller_check:
        controller_utils.check_cluster_name_not_controller(
            cluster_name, operation_str='konduktor.launch')

            handle = maybe_handle
            stages = [
                Stage.SYNC,
                Stage.EXEC,
                Stage.COMPLETED,
                Stage.FAILED,
            ]

    return _execute(
        entrypoint=entrypoint,
        dryrun=dryrun,
        down=down,
        stream_logs=stream_logs,
        handle=handle,
        backend=backend,
        retry_until_up=retry_until_up,
        optimize_target=optimize_target,
        stages=stages,
        cluster_name=cluster_name,
        detach_setup=detach_setup,
        detach_run=detach_run,
        idle_minutes_to_autostop=idle_minutes_to_autostop,
        no_setup=no_setup,
        clone_disk_from=clone_disk_from,
        _is_launched_by_jobs_controller=_is_launched_by_jobs_controller,
        _is_launched_by_konduktor_serve_controller=
        _is_launched_by_konduktor_serve_controller,
    )