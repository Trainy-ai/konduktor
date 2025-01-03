"""Resources: compute requirements of Tasks."""
import functools
from typing import Any, Dict, List, Optional, Union

from konduktor import logging
from konduktor.utils import accelerator_registry, common_utils, schemas

logger = logging.get_logger(__name__)

_DEFAULT_DISK_SIZE_GB = 256


class Resources:
    """Resources: compute requirements of Tasks.

    This class is immutable once created (to ensure some validations are done
    whenever properties change). To update the property of an instance of
    Resources, use `resources.copy(**new_properties)`.

    Used:

    * for representing resource requests for task

    """
    # If any fields changed, increment the version. For backward compatibility,
    # modify the __setstate__ method to handle the old version.
    _VERSION = 1

    def __init__(
        self,
        cloud: Optional[Any] = None,
        cpus: Union[None, int, float, str] = None,
        memory: Union[None, int, float, str] = None,
        accelerators: Union[str] = None,
        image_id: Union[Dict[str, str], str, None] = None,
        disk_size: Optional[int] = None,
        labels: Optional[Dict[str, str]] = None,
        # Internal use only.
        # pylint: disable=invalid-name
    ):
        """Initialize a Resources object.

        All fields are optional.  ``Resources.is_launchable`` decides whether
        the Resources is fully specified to launch an instance.

        Examples:
          .. code-block:: python

            # Specifying required resources; the system decides the
            # cloud/instance type. The below are equivalent:
            konduktor.Resources(accelerators='V100')
            konduktor.Resources(accelerators='V100:1')
            konduktor.Resources(accelerators={'V100': 1})
            konduktor.Resources(cpus='2+', memory='16+', accelerators='V100')

        Args:
          cloud: the cloud to use. (deprecated) all jobs are submitted to k8s
          instance_type: the instance type to use.
          cpus: the number of CPUs required for the task.
            If a str, must be a string of the form ``'2'`` or ``'2+'``, where
            the ``+`` indicates that the task requires at least 2 CPUs.
          memory: the amount of memory in GiB required. If a
            str, must be a string of the form ``'16'`` or ``'16+'``, where
            the ``+`` indicates that the task requires at least 16 GB of memory.
          accelerators: the accelerators required. If a str, must be
            a string of the form ``'V100'`` or ``'V100:2'``, where the ``:2``
            indicates that the task requires 2 V100 GPUs. If a dict, must be a
            dict of the form ``{'V100': 2}`` or ``{'tpu-v2-8': 1}``.

          image_id: docker image to use

          disk_size: the size of the OS disk in GiB.
          labels: the labels to apply to the instance. These are useful for
            assigning metadata that may be used by external tools.
            Implementation depends on the chosen cloud - On AWS, labels map to
            instance tags. On GCP, labels map to instance labels. On
            Kubernetes, labels map to pod labels. On other clouds, labels are
            not supported and will be ignored.
        Raises:
            ValueError: if some attributes are invalid.
            exceptions.NoCloudAccessError: if no public cloud is enabled.
        """
        self._version = self._VERSION
        if cloud is not None:
            raise ValueError("cloud specified, but all jobs are submitted to k8s")
        self._cloud = cloud

        if disk_size is not None:
            if round(disk_size) != disk_size:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        f'OS disk size must be an integer. Got: {disk_size}.')
            self._disk_size = int(disk_size)
        else:
            self._disk_size = _DEFAULT_DISK_SIZE_GB

        # self._image_id is a dict of {region: image_id}.
        # The key is None if the same image_id applies for all regions.
        self._image_id = image_id
        if isinstance(image_id, str):
            self._image_id = image_id.strip()

        self._labels = labels

        self._set_cpus(cpus)
        self._set_memory(memory)
        self._set_accelerators(accelerators)

        # TODO: move these out of init to prevent repeated calls.
        self._try_validate_cpus_mem()

    def __repr__(self) -> str:
        """Returns a string representation for display.

        Examples:

            >>> konduktor.Resources(accelerators='V100')
            <Kubernetes>({'V100': 1})

        """
        accelerators = ''
        if self.accelerators is not None:
            accelerators = f', {self.accelerators}'

        cpus = ''
        if self._cpus is not None:
            cpus = f', cpus={self._cpus}'

        memory = ''
        if self.memory is not None:
            memory = f', mem={self.memory}'

        image_id = ''
        if self.image_id is not None:
            if None in self.image_id:
                image_id = f', image_id={self.image_id[None]}'
            else:
                image_id = f', image_id={self.image_id}'

        disk_size = ''
        if self.disk_size != _DEFAULT_DISK_SIZE_GB:
            disk_size = f', disk_size={self.disk_size}'


        # Do not show region/zone here as `konduktor status -a` would show them as
        # separate columns. Also, Resources repr will be printed during
        # failover, and the region may be dynamically determined.
        hardware_str = (
            f'{cpus}{memory}{accelerators}{image_id}'
            f'{disk_size}')
        # It may have leading ',' (for example, instance_type not set) or empty
        # spaces.  Remove them.
        while hardware_str and hardware_str[0] in (',', ' '):
            hardware_str = hardware_str[1:]

        return f'({hardware_str})'

    @property
    def cloud(self):
        return self._cloud

    @property
    @functools.lru_cache(maxsize=1)
    def cpus(self) -> Optional[str]:
        """Returns the number of vCPUs that each instance must have.

        For example, cpus='4' means each instance must have exactly 4 vCPUs,
        and cpus='4+' means each instance must have at least 4 vCPUs.

        (Developer note: The cpus field is only used to select the instance type
        at launch time. Thus, Resources in the backend's ResourceHandle will
        always have the cpus field set to None.)
        """
        if self._cpus is not None:
            return self._cpus
        return None

    @property
    def memory(self) -> Optional[str]:
        """Returns the memory that each instance must have in GB.

        For example, memory='16' means each instance must have exactly 16GB
        memory; memory='16+' means each instance must have at least 16GB
        memory.

        (Developer note: The memory field is only used to select the instance
        type at launch time. Thus, Resources in the backend's ResourceHandle
        will always have the memory field set to None.)
        """
        return self._memory

    @property
    @functools.lru_cache(maxsize=1)
    def accelerators(self) -> Optional[Dict[str, Union[int, float]]]:
        """Returns the accelerators field directly or by inferring.

        For example, Resources(AWS, 'p3.2xlarge') has its accelerators field
        set to None, but this function will infer {'V100': 1} from the instance
        type.
        """
        if self._accelerators is not None:
            return self._accelerators
        return None

    @property
    def disk_size(self) -> int:
        return self._disk_size

    @property
    def image_id(self) -> Optional[Dict[str, str]]:
        return self._image_id

    @property
    def labels(self) -> Optional[Dict[str, str]]:
        return self._labels

    @property
    def cluster_config_overrides(self) -> Dict[str, Any]:
        if self._cluster_config_overrides is None:
            return {}
        return self._cluster_config_overrides

    def _set_cpus(
        self,
        cpus: Union[None, int, float, str],
    ) -> None:
        if cpus is None:
            self._cpus = None
            return

        self._cpus = str(cpus)
        if isinstance(cpus, str):
            if cpus.endswith('+'):
                num_cpus_str = cpus[:-1]
            else:
                num_cpus_str = cpus

            try:
                num_cpus = float(num_cpus_str)
            except ValueError:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        f'The "cpus" field should be either a number or '
                        f'a string "<number>+". Found: {cpus!r}') from None
        else:
            num_cpus = float(cpus)

        if num_cpus <= 0:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(
                    f'The "cpus" field should be positive. Found: {cpus!r}')

    def _set_memory(
        self,
        memory: Union[None, int, float, str],
    ) -> None:
        if memory is None:
            self._memory = None
            return

        self._memory = str(memory)
        if isinstance(memory, str):
            if memory.endswith(('+', 'x')):
                # 'x' is used internally for make sure our resources used by
                # jobs controller (memory: 3x) to have enough memory based on
                # the vCPUs.
                num_memory_gb = memory[:-1]
            else:
                num_memory_gb = memory

            try:
                memory_gb = float(num_memory_gb)
            except ValueError:
                with ux_utils.print_exception_no_traceback():
                    raise ValueError(
                        f'The "memory" field should be either a number or '
                        f'a string "<number>+". Found: {memory!r}') from None
        else:
            memory_gb = float(memory)

        if memory_gb <= 0:
            with ux_utils.print_exception_no_traceback():
                raise ValueError(
                    f'The "cpus" field should be positive. Found: {memory!r}')

    def _set_accelerators(
        self,
        accelerators: Union[None, str, Dict[str, int]],
        accelerator_args: Optional[Dict[str, str]] = None,
    ) -> None:
        """Sets accelerators.

        Args:
            accelerators: A string or a dict of accelerator types to counts.
            accelerator_args: (deprecated) A dict of accelerator types to args.
        """
        if accelerators is not None:
            if isinstance(accelerators, str):  # Convert to Dict[str, int].
                if ':' not in accelerators:
                    accelerators = {accelerators: 1}
                else:
                    splits = accelerators.split(':')
                    parse_error = ('The "accelerators" field as a str '
                                   'should be <name> or <name>:<cnt>. '
                                   f'Found: {accelerators!r}')
                    if len(splits) != 2:
                        with ux_utils.print_exception_no_traceback():
                            raise ValueError(parse_error)
                    try:
                        num = float(splits[1])
                        num = int(num) if num.is_integer() else num
                        accelerators = {splits[0]: num}
                    except ValueError:
                        with ux_utils.print_exception_no_traceback():
                            raise ValueError(parse_error) from None

            # Canonicalize the accelerator names.
            accelerators = {
                accelerator_registry.canonicalize_accelerator_name(
                    acc): acc_count
                for acc, acc_count in accelerators.items()
            }

            acc, _ = list(accelerators.items())[0]

        self._accelerators = accelerators


    def _try_validate_cpus_mem(self) -> None:
        """Try to validate the cpus and memory attributes.

        Raises:
            ValueError: if the attributes are invalid.
        """
        if self._cpus is None and self._memory is None:
            return


    def get_accelerators_str(self) -> str:
        accelerators = self.accelerators
        if accelerators is None:
            accelerators = '-'
        elif isinstance(accelerators, dict) and len(accelerators) == 1:
            accelerators, count = list(accelerators.items())[0]
            accelerators = f'{accelerators}:{count}'
        return accelerators

    def copy(self, **override) -> 'Resources':
        """Returns a copy of the given Resources."""
        resources = Resources(
            cloud=override.pop('cloud', self.cloud),
            cpus=override.pop('cpus', self._cpus),
            memory=override.pop('memory', self.memory),
            accelerators=override.pop('accelerators', self.accelerators),
            disk_size=override.pop('disk_size', self.disk_size),
            image_id=override.pop('image_id', self.image_id),
            labels=override.pop('labels', self.labels),
        )
        assert len(override) == 0
        return resources

    @classmethod
    def from_yaml_config(
        cls, config: Optional[Dict[str, Any]]
    ) -> 'Resources':
        if config is None:
            return {Resources()}
        common_utils.validate_schema(config, schemas.get_resources_schema(),
                                     'Invalid resources YAML: ')
        def _override_resources(
                base_resource_config: Dict[str, Any],
                override_configs: List[Dict[str, Any]]) -> List[Resources]:
            resources_list = []
            for override_config in override_configs:
                new_resource_config = base_resource_config.copy()
                # Labels are handled separately.
                override_labels = override_config.pop('labels', None)
                new_resource_config.update(override_config)

                # Update the labels with the override labels.
                labels = new_resource_config.get('labels', None)
                if labels is not None and override_labels is not None:
                    labels.update(override_labels)
                elif override_labels is not None:
                    labels = override_labels
                new_resource_config['labels'] = labels

                # Call from_yaml_config again instead of
                # _from_yaml_config_single to handle the case, where both
                # multiple accelerators and `any_of` is specified.
                # This will not cause infinite recursion because we have made
                # sure that `any_of` and `ordered` cannot be specified in the
                # resource candidates in `any_of` or `ordered`, by the schema
                # validation above.
                resources_list.extend(
                    list(Resources.from_yaml_config(new_resource_config)))

            return resources_list

        config = config.copy()

        return Resources._from_yaml_config_single(config)

    @classmethod
    def _from_yaml_config_single(cls, config: Dict[str, str]) -> 'Resources':

        resources_fields = {}
        resources_fields['cpus'] = config.pop('cpus', None)
        resources_fields['memory'] = config.pop('memory', None)
        resources_fields['accelerators'] = config.pop('accelerators', None)
        resources_fields['disk_size'] = config.pop('disk_size', None)
        resources_fields['image_id'] = config.pop('image_id', None)
        resources_fields['labels'] = config.pop('labels', None)

        if resources_fields['cpus'] is not None:
            resources_fields['cpus'] = str(resources_fields['cpus'])
        if resources_fields['memory'] is not None:
            resources_fields['memory'] = str(resources_fields['memory'])
        if resources_fields['disk_size'] is not None:
            resources_fields['disk_size'] = int(resources_fields['disk_size'])

        assert not config, f'Invalid resource args: {config.keys()}'
        return Resources(**resources_fields)

    def to_yaml_config(self) -> Dict[str, Union[str, int]]:
        """Returns a yaml-style dict of config for this resource bundle."""
        config = {}

        def add_if_not_none(key, value):
            if value is not None and value != 'None':
                config[key] = value

        add_if_not_none('cloud', str(self.cloud))
        add_if_not_none('instance_type', self.instance_type)
        add_if_not_none('cpus', self._cpus)
        add_if_not_none('memory', self.memory)
        add_if_not_none('accelerators', self.accelerators)

        add_if_not_none('disk_size', self.disk_size)
        add_if_not_none('image_id', self.image_id)
        add_if_not_none('labels', self.labels)
        return config
