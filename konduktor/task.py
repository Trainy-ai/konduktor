# Proprietary Changes made for Trainy under the Trainy Software License
# Original source: konduktor: https://github.com/konduktor-org/konduktor
# which is Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Task: a coarse-grained stage in an application."""
import inspect
import json
import os
import re
import typing
import yaml
from typing import (Any, Callable, Dict, Iterable, List, Optional, Set, Tuple,
                    Union)


import konduktor
from konduktor.data import storage as storage_lib
from konduktor.utils import common_utils
from konduktor.utils import schemas

_VALID_NAME_REGEX = '[a-zA-Z0-9]+(?:[._-]{1,2}[a-zA-Z0-9]+)*'
_VALID_NAME_DESCR = ('ASCII characters and may contain lowercase and'
                     ' uppercase letters, digits, underscores, periods,'
                     ' and dashes. Must start and end with alphanumeric'
                     ' characters. No triple dashes or underscores.')

_RUN_FN_CHECK_FAIL_MSG = (
    'run command generator must take exactly 2 arguments: node_rank (int) and'
    'a list of node ip addresses (List[str]). Got {run_sig}')


def _is_valid_name(name: Optional[str]) -> bool:
    """Checks if the task name is valid.

    Valid is defined as either NoneType or str with ASCII characters which may
    contain lowercase and uppercase letters, digits, underscores, periods,
    and dashes. Must start and end with alphanumeric characters.
    No triple dashes or underscores.

    Examples:
        some_name_here
        some-name-here
        some__name__here
        some--name--here
        some__name--here
        some.name.here
        some-name_he.re
        this---shouldnt--work
        this___shouldnt_work
        _thisshouldntwork
        thisshouldntwork_
    """
    if name is None:
        return True
    return bool(re.fullmatch(_VALID_NAME_REGEX, name))


def _fill_in_env_vars(
    yaml_field: Dict[str, Any],
    task_envs: Dict[str, str],
) -> Dict[str, Any]:
    """Detects env vars in yaml field and fills them with task_envs.

    Use cases of env vars in file_mounts:
    - dst/src paths; e.g.,
        /model_path/llama-${SIZE}b: s3://llama-weights/llama-${SIZE}b
    - storage's name (bucket name)
    - storage's source (local path)

    Use cases of env vars in service:
    - model type; e.g.,
        service:
          readiness_probe:
            path: /v1/chat/completions
            post_data:
              model: $MODEL_NAME
              messages:
                - role: user
                  content: How to print hello world?
              max_tokens: 1

    We simply dump yaml_field into a json string, and replace env vars using
    regex. This should be safe as yaml config has been schema-validated.

    Env vars of the following forms are detected:
        - ${ENV}
        - $ENV
    where <ENV> must appear in task.envs.
    """
    yaml_field_str = json.dumps(yaml_field)

    def replace_var(match):
        var_name = match.group(1)
        # If the variable isn't in the dictionary, return it unchanged
        return task_envs.get(var_name, match.group(0))

    # Pattern for valid env var names in bash.
    pattern = r'\$\{?\b([a-zA-Z_][a-zA-Z0-9_]*)\b\}?'
    yaml_field_str = re.sub(pattern, replace_var, yaml_field_str)
    return json.loads(yaml_field_str)


class Task:
    """Task: a computation to be run on the cloud."""

    def __init__(
        self,
        name: Optional[str] = None,
        *,
        setup: Optional[str] = None,
        run: Optional[str] = None,
        envs: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        num_nodes: Optional[int] = None,
        # Advanced:
        docker_image: Optional[str] = None,
        event_callback: Optional[str] = None,
        blocked_resources: Optional[Iterable['resources_lib.Resources']] = None,
    ):
        """Initializes a Task.

        All fields are optional.  ``Task.run`` is the actual program: either a
        shell command to run (str) or a command generator for different nodes
        (lambda; see below).

        Optionally, call ``Task.set_resources()`` to set the resource
        requirements for this task.  If not set, a default CPU-only requirement
        is assumed (the same as ``konduktor launch``).

        All setters of this class, ``Task.set_*()``, return ``self``, i.e.,
        they are fluent APIs and can be chained together.

        Example:
            .. code-block:: python

                # A Task that will sync up local workdir '.', containing
                # requirements.txt and train.py.
                konduktor.Task(setup='pip install requirements.txt',
                         run='python train.py',
                         workdir='.')

                # An empty Task for provisioning a cluster.
                task = konduktor.Task(num_nodes=n).set_resources(...)

                # Chaining setters.
                konduktor.Task().set_resources(...).set_file_mounts(...)

        Args:
          name: A string name for the Task for display purposes.
          run: The actual command for the task. If not None, either a shell
            command (str) or a command generator (callable).  If latter, it
            must take a node rank and a list of node addresses as input and
            return a shell command (str) (valid to return None for some nodes,
            in which case no commands are run on them).  Run commands will be
            run under ``workdir``. Note the command generator should be a
            self-contained lambda.
          envs: A dictionary of environment variables to set before running the
            setup and run commands.
          workdir: The local working directory.  This directory will be synced
            to a location on the remote VM(s), and ``setup`` and ``run``
            commands will be run under that location (thus, they can rely on
            relative paths when invoking binaries).
          num_nodes: The number of nodes to provision for this Task.  If None,
            treated as 1 node.  If > 1, each node will execute its own
            setup/run command, where ``run`` can either be a str, meaning all
            nodes get the same command, or a lambda, with the semantics
            documented above.
        """
        self.name = name
        self.run = run
        self.storage_mounts: Dict[str, storage_lib.Storage] = {}
        self.storage_plans: Dict[storage_lib.Storage,
                                 storage_lib.StoreType] = {}
        self._envs = envs or {}
        self.workdir = workdir
        self.docker_image = docker_image
        # Ignore type error due to a mypy bug.
        # https://github.com/python/mypy/issues/3004
        self._num_nodes = 1
        self.num_nodes = num_nodes  # type: ignore
        # Default to CPU VM
        self.resources: Union[List[konduktor.Resources],
                              Set[konduktor.Resources]] = {konduktor.Resources()}
        
        self.file_mounts: Optional[Dict[str, str]] = None

        # Check if the task is legal.
        self._validate()

    def _validate(self):
        """Checks if the Task fields are valid."""
        if not _is_valid_name(self.name):
            with ux_utils.print_exception_no_traceback():
                raise ValueError(f'Invalid task name {self.name}. Valid name: '
                                 f'{_VALID_NAME_DESCR}')

        # Check self.run
        if callable(self.run):
            run_sig = inspect.signature(self.run)
            # Check that run is a function with 2 arguments.
            if len(run_sig.parameters) != 2:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(_RUN_FN_CHECK_FAIL_MSG.format(run_sig))

            type_list = [int, List[str]]
            # Check annotations, if exists
            for i, param in enumerate(run_sig.parameters.values()):
                if param.annotation != inspect.Parameter.empty:
                    if param.annotation != type_list[i]:
                        with ux_utils.print_exception_no_traceback():
                            raise ValueError(
                                _RUN_FN_CHECK_FAIL_MSG.format(run_sig))

            # Check self containedness.
            run_closure = inspect.getclosurevars(self.run)
            if run_closure.nonlocals:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'run command generator must be self contained. '
                        f'Found nonlocals: {run_closure.nonlocals}')
            if run_closure.globals:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'run command generator must be self contained. '
                        f'Found globals: {run_closure.globals}')
            if run_closure.unbound:
                # Do not raise an error here. Import statements, which are
                # allowed, will be considered as unbounded.
                pass
        elif self.run is not None and not isinstance(self.run, str):
            with ux_utils.print_exception_no_traceback():
                raise ValueError('run must be a shell script (str), '
                                 f'Got {type(self.run)}')

        # Workdir.
        if self.workdir is not None:
            full_workdir = os.path.abspath(os.path.expanduser(self.workdir))
            if not os.path.isdir(full_workdir):
                # Symlink to a dir is legal (isdir() follows symlinks).
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'Workdir must exist and must be a directory (or '
                        f'a symlink to a directory). {self.workdir} not found.')

    @staticmethod
    def from_yaml_config(
        config: Dict[str, Any],
        env_overrides: Optional[List[Tuple[str, str]]] = None,
    ) -> 'Task':
        # More robust handling for 'envs': explicitly convert keys and values to
        # str, since users may pass '123' as keys/values which will get parsed
        # as int causing validate_schema() to fail.
        envs = config.get('envs')
        if envs is not None and isinstance(envs, dict):
            new_envs: Dict[str, Optional[str]] = {}
            for k, v in envs.items():
                if v is not None:
                    new_envs[str(k)] = str(v)
                else:
                    new_envs[str(k)] = None
            config['envs'] = new_envs
        common_utils.validate_schema(config, schemas.get_task_schema(),
                                     'Invalid task YAML: ')
        if env_overrides is not None:
            # We must override env vars before constructing the Task, because
            # the Storage object creation is eager and it (its name/source
            # fields) may depend on env vars.
            new_envs = config.get('envs', {})
            new_envs.update(env_overrides)
            config['envs'] = new_envs

        for k, v in config.get('envs', {}).items():
            if v is None:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        f'Environment variable {k!r} is None. Please set a '
                        'value for it in task YAML or with --env flag. '
                        f'To set it to be empty, use an empty string ({k}: "" '
                        f'in task YAML or --env {k}="" in CLI).')

        # Fill in any Task.envs into file_mounts (src/dst paths, storage
        # name/source).
        if config.get('file_mounts') is not None:
            config['file_mounts'] = _fill_in_env_vars(config['file_mounts'],
                                                      config.get('envs', {}))

        # Fill in any Task.envs into workdir
        if config.get('workdir') is not None:
            config['workdir'] = _fill_in_env_vars(config['workdir'],
                                                  config.get('envs', {}))

        task = Task(
            config.pop('name', None),
            run=config.pop('run', None),
            workdir=config.pop('workdir', None),
            setup=config.pop('setup', None),
            num_nodes=config.pop('num_nodes', None),
            envs=config.pop('envs', None),
        )

        # Create lists to store storage objects inlined in file_mounts.
        # These are retained in dicts in the YAML schema and later parsed to
        # storage objects with the storage/storage_mount objects.
        fm_storages = []
        file_mounts = config.pop('file_mounts', None)
        if file_mounts is not None:
            copy_mounts = {}
            for dst_path, src in file_mounts.items():
                # Check if it is str path
                if isinstance(src, str):
                    copy_mounts[dst_path] = src
                # If the src is not a str path, it is likely a dict. Try to
                # parse storage object.
                elif isinstance(src, dict):
                    fm_storages.append((dst_path, src))
                else:
                    with ux_utils.print_exception_no_traceback():
                        raise ValueError(f'Unable to parse file_mount '
                                         f'{dst_path}:{src}')
            task.set_file_mounts(copy_mounts)


        # Experimental configs.
        experimnetal_configs = config.pop('experimental', None)
        cluster_config_override = None
        if experimnetal_configs is not None:
            cluster_config_override = experimnetal_configs.pop(
                'config_overrides', None)
            logger.debug('Overriding konduktor config with task-level config: '
                         f'{cluster_config_override}')
        assert not experimnetal_configs, ('Invalid task args: '
                                          f'{experimnetal_configs.keys()}')

        # Parse resources field.
        resources_config = config.pop('resources', {})
        if cluster_config_override is not None:
            assert resources_config.get('_cluster_config_overrides') is None, (
                'Cannot set _cluster_config_overrides in both resources and '
                'experimental.config_overrides')
            resources_config[
                '_cluster_config_overrides'] = cluster_config_override
        task.set_resources(konduktor.Resources.from_yaml_config(resources_config))
        assert not config, f'Invalid task args: {config.keys()}'
        return task

    @staticmethod
    def from_yaml(yaml_path: str) -> 'Task':
        """Initializes a task from a task YAML.

        Example:
            .. code-block:: python

                task = konduktor.Task.from_yaml('/path/to/task.yaml')

        Args:
          yaml_path: file path to a valid task yaml file.

        Raises:
          ValueError: if the path gets loaded into a str instead of a dict; or
            if there are any other parsing errors.
        """
        with open(os.path.expanduser(yaml_path), 'r', encoding='utf-8') as f:
            #  https://github.com/yaml/pyyaml/issues/165#issuecomment-430074049
            # to raise errors on duplicate keys.
            config = yaml.safe_load(f)

        if isinstance(config, str):
            with ux_utils.print_exception_no_traceback():
                raise ValueError('YAML loaded as str, not as dict. '
                                 f'Is it correct? Path: {yaml_path}')

        if config is None:
            config = {}
        return Task.from_yaml_config(config)

    @property
    def num_nodes(self) -> int:
        return self._num_nodes

    @num_nodes.setter
    def num_nodes(self, num_nodes: Optional[int]) -> None:
        if num_nodes is None:
            num_nodes = 1
        if not isinstance(num_nodes, int) or num_nodes <= 0:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(
                    f'num_nodes should be a positive int. Got: {num_nodes}')
        self._num_nodes = num_nodes

    @property
    def envs(self) -> Dict[str, str]:
        return self._envs

    def update_envs(
            self, envs: Union[None, List[Tuple[str, str]],
                              Dict[str, str]]) -> 'Task':
        """Updates environment variables for use inside the setup/run commands.

        Args:
          envs: (optional) either a list of ``(env_name, value)`` or a dict
            ``{env_name: value}``.

        Returns:
          self: The current task, with envs updated.

        Raises:
          ValueError: if various invalid inputs errors are detected.
        """
        if envs is None:
            envs = {}
        if isinstance(envs, (list, tuple)):
            keys = set(env[0] for env in envs)
            if len(keys) != len(envs):
                with ux_utils.print_exception_no_traceback():
                    raise ValueError('Duplicate env keys provided.')
            envs = dict(envs)
        if isinstance(envs, dict):
            for key in envs:
                if not isinstance(key, str):
                    with ux_utils.print_exception_no_traceback():
                        raise ValueError('Env keys must be strings.')
                if not common_utils.is_valid_env_var(key):
                    with ux_utils.print_exception_no_traceback():
                        raise ValueError(f'Invalid env key: {key}')
        else:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(
                    'envs must be List[Tuple[str, str]] or Dict[str, str]: '
                    f'{envs}')
        self._envs.update(envs)
        return self

    def set_resources(
        self, resources: Union['resources_lib.Resources',
                               List['resources_lib.Resources'],
                               Set['resources_lib.Resources']]
    ) -> 'Task':
        """Sets the required resources to execute this task.

        If this function is not called for a Task, default resource
        requirements will be used (8 vCPUs).

        Args:
          resources: either a konduktor.Resources, a set of them, or a list of them.
            A set or a list of resources asks the optimizer to "pick the
            best of these resources" to run this task.
        Returns:
          self: The current task, with resources set.
        """
        if isinstance(resources, konduktor.Resources):
            resources = {resources}
        self.resources = resources

        return self

    def set_resources_override(self, override_params: Dict[str, Any]) -> 'Task':
        """Sets the override parameters for the resources."""
        new_resources_list = []
        for res in list(self.resources):
            new_resources = res.copy(**override_params)
            new_resources_list.append(new_resources)

        self.set_resources(type(self.resources)(new_resources_list))
        return self


    def set_file_mounts(self, file_mounts: Optional[Dict[str, str]]) -> 'Task':
        """Sets the file mounts for this task.

        Useful for syncing datasets, dotfiles, etc.

        File mounts are a dictionary: ``{remote_path: local_path/cloud URI}``.
        Local (or cloud) files/directories will be synced to the specified
        paths on the remote VM(s) where this Task will run.

        Neither source or destimation paths can end with a slash.

        Example:
            .. code-block:: python

                task.set_file_mounts({
                    '~/.dotfile': '/local/.dotfile',
                    # /remote/dir/ will contain the contents of /local/dir/.
                    '/remote/dir': '/local/dir',
                })

        Args:
          file_mounts: an optional dict of ``{remote_path: local_path/cloud
            URI}``, where remote means the VM(s) on which this Task will
            eventually run on, and local means the node from which the task is
            launched.

        Returns:
          self: the current task, with file mounts set.

        Raises:
          ValueError: if input paths are invalid.
        """
        if file_mounts is None:
            self.file_mounts = None
            return self
        for target, source in file_mounts.items():
            if target.endswith('/') or source.endswith('/'):
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'File mount paths cannot end with a slash '
                        '(try "/mydir: /mydir" or "/myfile: /myfile"). '
                        f'Found: target={target} source={source}')
            if data_utils.is_cloud_store_url(target):
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        'File mount destination paths cannot be cloud storage')
            if not data_utils.is_cloud_store_url(source):
                if (not os.path.exists(
                        os.path.abspath(os.path.expanduser(source))) and
                        not source.startswith('konduktor:')):
                    with ux_utils.print_exception_no_traceback():
                        raise ValueError(
                            f'File mount source {source!r} does not exist '
                            'locally. To fix: check if it exists, and correct '
                            'the path.')
            if (target == constants.SKY_REMOTE_WORKDIR and
                    self.workdir is not None):
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        f'Cannot use {constants.SKY_REMOTE_WORKDIR!r} as a '
                        'destination path of a file mount, as it will be used '
                        'by the workdir. If uploading a file/folder to the '
                        'workdir is needed, please specify the full path to '
                        'the file/folder.')

        self.file_mounts = file_mounts
        return self


    # (asaiacai)TODO: this will probably be reduced by a lot
    def _get_preferred_store(
            self) -> Tuple[storage_lib.StoreType, Optional[str]]:
        """Returns the preferred store type and region for this task."""
        storage_cloud = None

        enabled_storage_clouds = (
            storage_lib.get_cached_enabled_storage_clouds_or_refresh(
                raise_if_no_cloud_access=True))

        if self.best_resources is not None:
            storage_cloud = self.best_resources.cloud
            storage_region = self.best_resources.region
        else:
            resources = list(self.resources)[0]
            storage_cloud = resources.cloud
            storage_region = resources.region

        if storage_cloud is not None:
            if str(storage_cloud) not in enabled_storage_clouds:
                storage_cloud = None

        storage_cloud_str = None
        if storage_cloud is None:
            storage_cloud_str = enabled_storage_clouds[0]
            assert storage_cloud_str is not None, enabled_storage_clouds[0]
            storage_region = None  # Use default region in the Store class
        else:
            storage_cloud_str = str(storage_cloud)

        store_type = storage_lib.StoreType.from_cloud(storage_cloud_str)
        return store_type, storage_region

    def sync_storage_mounts(self) -> None:
        """(INTERNAL) Eagerly syncs storage mounts to cloud storage.

        After syncing up, COPY-mode storage mounts are translated into regular
        file_mounts of the form ``{ /remote/path: {s3,gs,..}://<bucket path>
        }``. For local file mounts, we first sync all local paths from
        `workdir` and `file_mounts` to 
        """
        # TODO(asaiacai): this needs to be done
        for storage in self.storage_mounts.values():
            if len(storage.stores) == 0:
                store_type, store_region = self._get_preferred_store()
                self.storage_plans[storage] = store_type
                storage.add_store(store_type, store_region)
            else:
                # We will download the first store that is added to remote.
                self.storage_plans[storage] = list(storage.stores.keys())[0]

        storage_mounts = self.storage_mounts
        storage_plans = self.storage_plans
        for mnt_path, storage in storage_mounts.items():
            if storage.mode == storage_lib.StorageMode.COPY:
                store_type = storage_plans[storage]
            else:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(f'Storage Type {store_type} '
                                        'does not exist!')

    def get_local_to_remote_file_mounts(self) -> Optional[Dict[str, str]]:
        """Returns file mounts of the form (dst=VM path, src=local path).

        Any cloud object store URIs (gs://, s3://, etc.), either as source or
        destination, are not included.

        INTERNAL: this method is internal-facing.
        """
        if self.file_mounts is None:
            return None
        d = {}
        for k, v in self.file_mounts.items():
            if not data_utils.is_cloud_store_url(
                    k) and not data_utils.is_cloud_store_url(v):
                d[k] = v
        return d


    def to_yaml_config(self) -> Dict[str, Any]:
        """Returns a yaml-style dict representation of the task.

        INTERNAL: this method is internal-facing.
        """
        config = {}

        def add_if_not_none(key, value, no_empty: bool = False):
            if no_empty and not value:
                return
            if value is not None:
                config[key] = value

        add_if_not_none('name', self.name)

        tmp_resource_config = {}
        if len(self.resources) > 1:
            resource_list = []
            for r in self.resources:
                resource_list.append(r.to_yaml_config())
            key = 'ordered' if isinstance(self.resources, list) else 'any_of'
            tmp_resource_config[key] = resource_list
        else:
            tmp_resource_config = list(self.resources)[0].to_yaml_config()

        add_if_not_none('resources', tmp_resource_config)

        if self.service is not None:
            add_if_not_none('service', self.service.to_yaml_config())

        add_if_not_none('num_nodes', self.num_nodes)

        if self.inputs is not None:
            add_if_not_none('inputs',
                            {self.inputs: self.estimated_inputs_size_gigabytes})
        if self.outputs is not None:
            add_if_not_none(
                'outputs',
                {self.outputs: self.estimated_outputs_size_gigabytes})

        add_if_not_none('setup', self.setup)
        add_if_not_none('run', self.run)
        add_if_not_none('workdir', self.workdir)
        add_if_not_none('envs', self.envs, no_empty=True)

        add_if_not_none('file_mounts', {})

        if self.file_mounts is not None:
            config['file_mounts'].update(self.file_mounts)

        if self.storage_mounts is not None:
            config['file_mounts'].update({
                mount_path: storage.to_yaml_config()
                for mount_path, storage in self.storage_mounts.items()
            })
        return config