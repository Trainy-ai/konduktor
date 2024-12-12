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

"""The 'konduktor' command line tool.

Example usage:

  # See available commands.
  >> konduktor

  # Run a task, described in a yaml file.
  >> konduktor launch task.yaml

  # Show the list of scheduled jobs
  >> konduktor status

  # Tear down a specific job.
  >> konduktor down cluster_name

  # Tear down all scheduled jobs
  >> konduktor down -a

NOTE: the order of command definitions in this file corresponds to how they are
listed in "konduktor --help".  Take care to put logically connected commands close to
each other.
"""

import click
import dotenv
import shlex
import yaml

from typing import Any, Dict, List, Tuple, Optional, Union

import konduktor
from konduktor.utils import common_utils

_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def _parse_env_var(env_var: str) -> Tuple[str, str]:
    """Parse env vars into a (KEY, VAL) pair."""
    if '=' not in env_var:
        value = os.environ.get(env_var)
        if value is None:
            raise click.UsageError(
                f'{env_var} is not set in local environment.')
        return (env_var, value)
    ret = tuple(env_var.split('=', 1))
    if len(ret) != 2:
        raise click.UsageError(
            f'Invalid env var: {env_var}. Must be in the form of KEY=VAL '
            'or KEY.')
    return ret[0], ret[1]


def _merge_env_vars(env_dict: Optional[Dict[str, str]],
                    env_list: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Merges all values from env_list into env_dict."""
    if not env_dict:
        return env_list
    for (key, value) in env_list:
        env_dict[key] = value
    return list(env_dict.items())


def _make_task_with_overrides(
    entrypoint: Tuple[str, ...],
    *,
    entrypoint_name: str = 'konduktor.Task',
    name: Optional[str] = None,
    workdir: Optional[str] = None,
    cloud: Optional[str] = None,
    gpus: Optional[str] = None,
    cpus: Optional[str] = None,
    memory: Optional[str] = None,
    instance_type: Optional[str] = None,
    num_nodes: Optional[int] = None,
    image_id: Optional[str] = None,
    disk_size: Optional[int] = None,
    env: Optional[List[Tuple[str, str]]] = None,
    field_to_ignore: Optional[List[str]] = None,
) -> konduktor.Task:
    """Creates a task or a dag from an entrypoint with overrides.

    Returns:
        konduktor.Task
    """
    entrypoint = ' '.join(entrypoint)
    is_yaml, _ = _check_yaml(entrypoint)
    entrypoint: Optional[str]
    if is_yaml:
        # Treat entrypoint as a yaml.
        click.secho(f'{entrypoint_name} from YAML spec: ',
                    fg='yellow',
                    nl=False)
        click.secho(entrypoint, bold=True)
    else:
        if not entrypoint:
            entrypoint = None
        else:
            # Treat entrypoint as a bash command.
            click.secho(f'{entrypoint_name} from command: ',
                        fg='yellow',
                        nl=False)
            click.secho(entrypoint, bold=True)

    override_params = _parse_override_params(cloud=cloud,
                                             gpus=gpus,
                                             cpus=cpus,
                                             memory=memory,
                                             image_id=image_id,
                                             disk_size=disk_size,)

    if field_to_ignore is not None:
        _pop_and_ignore_fields_in_override_params(override_params,
                                                  field_to_ignore)

    if is_yaml:
        assert entrypoint is not None
        task_configs = common_utils.read_yaml_all(entrypoint)
        assert len(task_configs) == 1, "Only single tasks are supported"
        task = konduktor.Task.from_yaml_config(task_configs[0], env)
    else:
        task = konduktor.Task(name='konduktor-cmd', run=entrypoint)
        task.set_resources({konduktor.Resources()})
        task.update_envs(env)

    # Override.
    if workdir is not None:
        task.workdir = workdir

    task.set_resources_override(override_params)

    if num_nodes is not None:
        task.num_nodes = num_nodes
    if name is not None:
        task.name = name
    return task


_TASK_OPTIONS = [
    click.option(
        '--workdir',
        required=False,
        type=click.Path(exists=True, file_okay=False),
        help=('If specified, sync this dir to the remote working directory, '
              'where the task will be invoked. '
              'Overrides the "workdir" config in the YAML if both are supplied.'
             )),
    click.option(
        '--cloud',
        required=False,
        type=str,
        help=('The cloud to use. If specified, overrides the "resources.cloud" '
              'config. Passing "none" resets the config. [defunct] currently '
              'only supports a single cloud')),
    click.option(
        '--num-nodes',
        required=False,
        type=int,
        help=('Number of nodes to execute the task on. '
              'Overrides the "num_nodes" config in the YAML if both are '
              'supplied.')),
    click.option(
        '--cpus',
        default=None,
        type=str,
        required=False,
        help=('Number of vCPUs each instance must have (e.g., '
              '``--cpus=4`` (exactly 4) or ``--cpus=4+`` (at least 4)). '
              'This is used to automatically select the instance type.')),
    click.option(
        '--memory',
        default=None,
        type=str,
        required=False,
        help=(
            'Amount of memory each instance must have in GB (e.g., '
            '``--memory=16`` (exactly 16GB), ``--memory=16+`` (at least 16GB))'
        )),
    click.option('--disk-size',
                 default=None,
                 type=int,
                 required=False,
                 help=('OS disk size in GBs.')),
    click.option('--image-id',
                 required=False,
                 default=None,
                 help=('Custom image id for launching the instances. '
                       'Passing "none" resets the config.')),
    click.option('--env-file',
                 required=False,
                 type=dotenv.dotenv_values,
                 help="""\
        Path to a dotenv file with environment variables to set on the remote
        node.

        If any values from ``--env-file`` conflict with values set by
        ``--env``, the ``--env`` value will be preferred."""),
    click.option(
        '--env',
        required=False,
        type=_parse_env_var,
        multiple=True,
        help="""\
        Environment variable to set on the remote node.
        It can be specified multiple times.
        Examples:

        \b
        1. ``--env MY_ENV=1``: set ``$MY_ENV`` on the cluster to be 1.

        2. ``--env MY_ENV2=$HOME``: set ``$MY_ENV2`` on the cluster to be the
        same value of ``$HOME`` in the local environment where the CLI command
        is run.

        3. ``--env MY_ENV3``: set ``$MY_ENV3`` on the cluster to be the
        same value of ``$MY_ENV3`` in the local environment.""",
    )
]
_TASK_OPTIONS_WITH_NAME = [
    click.option('--name',
                 '-n',
                 required=False,
                 type=str,
                 help=('Task name. Overrides the "name" '
                       'config in the YAML if both are supplied.')),
] + _TASK_OPTIONS
_EXTRA_RESOURCES_OPTIONS = [
    click.option(
        '--gpus',
        required=False,
        type=str,
        help=
        ('Type and number of GPUs to use. Example values: '
         '"V100:8", "V100" (short for a count of 1), or "V100:0.5" '
         '(fractional counts are supported by the scheduling framework). '
         'If a new cluster is being launched by this command, this is the '
         'resources to provision. If an existing cluster is being reused, this'
         ' is seen as the task demand, which must fit the cluster\'s total '
         'resources and is used for scheduling the task. '
         'Overrides the "accelerators" '
         'config in the YAML if both are supplied. '
         'Passing "none" resets the config.')),
]


def _get_click_major_version():
    return int(click.__version__.split('.', maxsplit=1)[0])


_RELOAD_ZSH_CMD = 'source ~/.zshrc'
_RELOAD_BASH_CMD = 'source ~/.bashrc'


def _add_click_options(options: List[click.Option]):
    """A decorator for adding a list of click option decorators."""

    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def _parse_override_params(
        cloud: Optional[str] = None,
        gpus: Optional[str] = None,
        cpus: Optional[str] = None,
        memory: Optional[str] = None,
        image_id: Optional[str] = None,
        disk_size: Optional[int] = None,) -> Dict[str, Any]:
    """Parses the override parameters into a dictionary."""
    override_params: Dict[str, Any] = {}
    if cloud is not None:
        if cloud.lower() == 'none':
            override_params['cloud'] = None
        else:
            override_params['cloud'] = konduktor_clouds.CLOUD_REGISTRY.from_str(cloud)
    if gpus is not None:
        if gpus.lower() == 'none':
            override_params['accelerators'] = None
        else:
            override_params['accelerators'] = gpus
    if cpus is not None:
        if cpus.lower() == 'none':
            override_params['cpus'] = None
        else:
            override_params['cpus'] = cpus
    if memory is not None:
        if memory.lower() == 'none':
            override_params['memory'] = None
        else:
            override_params['memory'] = memory
    if image_id is not None:
        if image_id.lower() == 'none':
            override_params['image_id'] = None
        else:
            override_params['image_id'] = image_id
    if disk_size is not None:
        override_params['disk_size'] = disk_size
    return override_params


def _launch_with_confirm(
    task: konduktor.Task,
    *,
    dryrun: bool,
    detach_run: bool,
    detach_setup: bool = False,
    no_confirm: bool = False,
):
    """Launch a cluster with a Task."""

    konduktor.launch(
        task,
        dryrun=dryrun,
        stream_logs=True,
        cluster_name=cluster,
        detach_setup=detach_setup,
        detach_run=detach_run,
        down=down,
    )


def _check_yaml(entrypoint: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Checks if entrypoint is a readable YAML file.

    Args:
        entrypoint: Path to a YAML file.
    """
    is_yaml = True
    config: Optional[List[Dict[str, Any]]] = None
    result = None
    shell_splits = shlex.split(entrypoint)
    yaml_file_provided = (len(shell_splits) == 1 and
                          (shell_splits[0].endswith('yaml') or
                           shell_splits[0].endswith('.yml')))
    invalid_reason = ''
    try:
        with open(entrypoint, 'r', encoding='utf-8') as f:
            try:
                config = list(yaml.safe_load_all(f))
                if config:
                    result = config[0]
                else:
                    result = {}
                if isinstance(result, str):
                    # 'konduktor exec cluster ./my_script.sh'
                    is_yaml = False
            except yaml.YAMLError as e:
                if yaml_file_provided:
                    logger.debug(e)
                    detailed_error = f'\nYAML Error: {e}\n'
                    invalid_reason = ('contains an invalid configuration. '
                                      'Please check syntax.\n'
                                      f'{detailed_error}')
                is_yaml = False

    except OSError:
        if yaml_file_provided:
            entry_point_path = os.path.expanduser(entrypoint)
            if not os.path.exists(entry_point_path):
                invalid_reason = ('does not exist. Please check if the path'
                                  ' is correct.')
            elif not os.path.isfile(entry_point_path):
                invalid_reason = ('is not a file. Please check if the path'
                                  ' is correct.')
            else:
                invalid_reason = ('yaml.safe_load() failed. Please check if the'
                                  ' path is correct.')
        is_yaml = False
    if not is_yaml:
        if yaml_file_provided:
            click.confirm(
                f'{entrypoint!r} looks like a yaml path but {invalid_reason}\n'
                'It will be treated as a command to be run remotely. Continue?',
                abort=True)
    return is_yaml, result


def _pop_and_ignore_fields_in_override_params(
        params: Dict[str, Any], field_to_ignore: List[str]) -> None:
    """Pops and ignores fields in override params.

    Args:
        params: Override params.
        field_to_ignore: Fields to ignore.

    Returns:
        Override params with fields ignored.
    """
    if field_to_ignore is not None:
        for field in field_to_ignore:
            field_value = params.pop(field, None)
            if field_value is not None:
                click.secho(f'Override param {field}={field_value} is ignored.',
                            fg='yellow')

class _NaturalOrderGroup(click.Group):
    """Lists commands in the order defined in this script.

    Reference: https://github.com/pallets/click/issues/513
    """

    def list_commands(self, ctx):
        return self.commands.keys()

    def invoke(self, ctx):
        return super().invoke(ctx)


class _DocumentedCodeCommand(click.Command):
    """Corrects help strings for documented commands such that --help displays
    properly and code blocks are rendered in the official web documentation.
    """

    def get_help(self, ctx):
        help_str = ctx.command.help
        ctx.command.help = help_str.replace('.. code-block:: bash\n', '\b')
        return super().get_help(ctx)


def _with_deprecation_warning(
        f,
        original_name: str,
        alias_name: str,
        override_command_argument: Optional[Dict[str, Any]] = None):

    @functools.wraps(f)
    def wrapper(self, *args, **kwargs):
        override_str = ''
        if override_command_argument is not None:
            overrides = []
            for k, v in override_command_argument.items():
                if isinstance(v, bool):
                    if v:
                        overrides.append(f'--{k}')
                    else:
                        overrides.append(f'--no-{k}')
                else:
                    overrides.append(f'--{k.replace("_", "-")}={v}')
            override_str = ' with additional arguments ' + ' '.join(overrides)
        click.secho(
            f'WARNING: `{alias_name}` has been renamed to `{original_name}` '
            f'and will be removed in a future release. Please use the '
            f'latter{override_str} instead.\n',
            err=True,
            fg='yellow')
        return f(self, *args, **kwargs)

    return wrapper


def _override_arguments(callback, override_command_argument: Dict[str, Any]):

    def wrapper(*args, **kwargs):
        logger.info(f'Overriding arguments: {override_command_argument}')
        kwargs.update(override_command_argument)
        return callback(*args, **kwargs)

    return wrapper


def _add_command_alias(
    group: click.Group,
    command: click.Command,
    hidden: bool = False,
    new_group: Optional[click.Group] = None,
    new_command_name: Optional[str] = None,
    override_command_argument: Optional[Dict[str, Any]] = None,
    with_warning: bool = True,
) -> None:
    """Add a alias of a command to a group."""
    if new_group is None:
        new_group = group
    if new_command_name is None:
        new_command_name = command.name
    if new_group == group and new_command_name == command.name:
        raise ValueError('Cannot add an alias to the same command.')
    new_command = copy.deepcopy(command)
    new_command.hidden = hidden
    new_command.name = new_command_name

    if override_command_argument:
        new_command.callback = _override_arguments(new_command.callback,
                                                   override_command_argument)

    orig = f'konduktor {group.name} {command.name}'
    alias = f'konduktor {new_group.name} {new_command_name}'
    if with_warning:
        new_command.invoke = _with_deprecation_warning(
            new_command.invoke,
            orig,
            alias,
            override_command_argument=override_command_argument)
    new_group.add_command(new_command, name=new_command_name)


def _deprecate_and_hide_command(group, command_to_deprecate,
                                alternative_command):
    """Hide a command and show a deprecation note, hinting the alternative."""
    command_to_deprecate.hidden = True
    if group is not None:
        orig = f'konduktor {group.name} {command_to_deprecate.name}'
    else:
        orig = f'konduktor {command_to_deprecate.name}'
    command_to_deprecate.invoke = _with_deprecation_warning(
        command_to_deprecate.invoke, alternative_command, orig)

@click.group(cls=_NaturalOrderGroup, context_settings=_CONTEXT_SETTINGS)
@click.version_option(konduktor.__version__, '--version', '-v', prog_name='konduktor')
@click.version_option(konduktor.__commit__,
                      '--commit',
                      '-c',
                      prog_name='konduktor',
                      message='%(prog)s, commit %(version)s',
                      help='Show the commit hash and exit')
def cli():
    pass


@cli.command(cls=_DocumentedCodeCommand)
@click.argument('entrypoint',
                required=False,
                type=str,
                nargs=-1,
                )
@click.option('--workload',
              '-w',
              default=None,
              type=str,)
@click.option('--dryrun',
              default=False,
              is_flag=True,
              help='If True, do not actually run the job.')
@click.option(
    '--detach-setup',
    '-s',
    default=False,
    is_flag=True,
    help=
    ('If True, run setup in non-interactive mode as part of the job itself. '
     'You can safely ctrl-c to detach from logging, and it will not interrupt '
     'the setup process. To see the logs again after detaching, use `konduktor logs`.'
     ' To cancel setup, cancel the job via `konduktor cancel`. Useful for long-'
     'running setup commands.'))
@click.option(
    '--detach-run',
    '-d',
    default=False,
    is_flag=True,
    help=('If True, as soon as a job is submitted, return from this call '
          'and do not stream execution logs.'))
@_add_click_options(_TASK_OPTIONS_WITH_NAME + _EXTRA_RESOURCES_OPTIONS)
@click.option(
    '--yes',
    '-y',
    is_flag=True,
    default=False,
    required=False,
    # Disabling quote check here, as there seems to be a bug in pylint,
    # which incorrectly recognizes the help string as a docstring.
    # pylint: disable=bad-docstring-quotes
    help='Skip confirmation prompt.')
def launch(
    entrypoint: Tuple[str, ...],
    #TODO(asaiacai): rename cluster to workload
    workload: Optional[str],
    dryrun: bool,
    detach_setup: bool,
    detach_run: bool,
    name: Optional[str],
    workdir: Optional[str],
    cloud: Optional[str],
    gpus: Optional[str],
    cpus: Optional[str],
    memory: Optional[str],
    num_nodes: Optional[int],
    image_id: Optional[str],
    env_file: Optional[Dict[str, str]],
    env: List[Tuple[str, str]],
    disk_size: Optional[int],
    yes: bool,
):
    """Launch a task.

    If ENTRYPOINT points to a valid YAML file, it is read in as the task
    specification. Otherwise, it is interpreted as a bash command.
    """
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    env = _merge_env_vars(env_file, env)

    task = _make_task_with_overrides(
        entrypoint=entrypoint,
        name=name,
        workdir=workdir,
        cloud=cloud,
        gpus=gpus,
        cpus=cpus,
        memory=memory,
        num_nodes=num_nodes,
        image_id=image_id,
        env=env,
        disk_size=disk_size,
    )

    _launch_with_confirm(task,
                         dryrun=dryrun,
                         detach_setup=detach_setup,
                         detach_run=detach_run,
                         no_confirm=yes,
                         )


@cli.command()
@click.argument('queues',
                required=False,
                type=str,
                nargs=-1,
                )
# pylint: disable=redefined-builtin
def status(all: bool, refresh: bool, ip: bool, endpoints: bool,
           endpoint: Optional[int], show_managed_jobs: bool,
           show_services: bool, kubernetes: bool, clusters: List[str]):
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Show queues and workloads
    """


@cli.command(cls=_DocumentedCodeCommand)
@click.argument('workload_ids',
                nargs=-1,
                required=False,
                )
@click.option('--all',
              '-a',
              default=None,
              is_flag=True,
              help='Tear down all jobs.')
@click.option('--yes',
              '-y',
              is_flag=True,
              default=False,
              required=False,
              help='Skip confirmation prompt.')
@click.option(
    '--purge',
    '-p',
    is_flag=True,
    default=False,
    required=False,
    help=('(Advanced) Forcefully delete workloads'))
def down(
    clusters: List[str],
    all: Optional[bool],  # pylint: disable=redefined-builtin
    yes: bool,
    purge: bool,
):
    # NOTE(dev): Keep the docstring consistent between the Python API and CLI.
    """Tear down cluster(s).

    CLUSTER is the name of the cluster (or glob pattern) to tear down.  If both
    CLUSTER and ``--all`` are supplied, the latter takes precedence.

    Tearing down a cluster will delete all associated resources (all billing
    stops), and any data on the attached disks will be lost.  Accelerators
    (e.g., TPUs) that are part of the cluster will be deleted too.


    Examples:

    .. code-block:: bash

      # Tear down a specific cluster.
      konduktor down cluster_name
      \b
      # Tear down multiple clusters.
      konduktor down cluster1 cluster2
      \b
      # Tear down all clusters matching glob pattern 'cluster*'.
      konduktor down "cluster*"
      \b
      # Tear down all existing clusters.
      konduktor down -a

    """
    _down_or_stop_clusters(clusters,
                           apply_to_all=all,
                           down=True,
                           no_confirm=yes,
                           purge=purge)


@cli.command(cls=_DocumentedCodeCommand)
@click.argument('clouds', required=False, type=str, nargs=-1)
@click.option('--verbose',
              '-v',
              is_flag=True,
              default=False,
              help='Show the activated account for each cloud.')
def check(clouds: Tuple[str], verbose: bool):
    """Check which clouds are available to use for storage

    This checks storage credentials for all clouds supported by konduktor. If a
    cloud is detected to be inaccessible, the reason and correction steps will
    be shown.

    If CLOUDS are specified, checks credentials for only those clouds.

    The enabled clouds are cached and form the "search space" to be considered
    for each task.

    Examples:

    .. code-block:: bash

      # Check credentials for all supported clouds.
      konduktor check
      \b
      # Check only specific clouds - AWS and GCP.
      konduktor check gcp
    """
    clouds_arg = clouds if len(clouds) > 0 else None
    konduktor_check.check(verbose=verbose, clouds=clouds_arg)


def main():
    return cli()


if __name__ == '__main__':
    main()