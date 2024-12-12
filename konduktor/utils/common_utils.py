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

import functools
import getpass
import hashlib
import inspect
import os
import socket
import sys
import uuid
import yaml

from typing import Any, Callable, Dict, List, Optional, Union

from konduktor.utils import constants
from konduktor.utils import schemas

_USER_HASH_FILE = os.path.expanduser('~/.konduktor/user_hash')
_usage_run_id = None
USER_HASH_LENGTH = 8
USER_HASH_LENGTH_IN_CLUSTER_NAME = 4

def user_and_hostname_hash() -> str:
    """Returns a string containing <user>-<hostname hash last 4 chars>.

    For uniquefying user workloads on a shared-k8s cluster.

    Using uuid.getnode() instead of gethostname() is incorrect; observed to
    collide on Macs.
    """
    hostname_hash = hashlib.md5(socket.gethostname().encode()).hexdigest()[-4:]
    return f'{getpass.getuser()}-{hostname_hash}'

def get_pretty_entry_point() -> str:
    """Returns the prettified entry point of this process (sys.argv).

    Example return values:
        $ konduktor launch app.yaml  # 'konduktor launch app.yaml'
        $ python examples/app.py  # 'app.py'
    """
    argv = sys.argv
    basename = os.path.basename(argv[0])
    if basename == 'konduktor':
        # Turn '/.../anaconda/envs/py36/bin/sky' into 'konduktor', but keep other
        # things like 'examples/app.py'.
        argv[0] = basename
    return ' '.join(argv)

def get_usage_run_id() -> str:
    """Returns a unique run id for each 'run'.

    A run is defined as the lifetime of a process that has imported `sky`
    and has called its CLI or programmatic APIs. For example, two successive
    `sky launch` are two runs.
    """
    global _usage_run_id
    if _usage_run_id is None:
        _usage_run_id = str(uuid.uuid4())
    return _usage_run_id

def make_decorator(cls, name_or_fn: Union[str, Callable],
                   **ctx_kwargs) -> Callable:
    """Make the cls a decorator.

    class cls:
        def __init__(self, name, **kwargs):
            pass
        def __enter__(self):
            pass
        def __exit__(self, exc_type, exc_value, traceback):
            pass

    Args:
        name_or_fn: The name of the event or the function to be wrapped.
        message: The message attached to the event.
    """
    if isinstance(name_or_fn, str):

        def _wrapper(f):

            @functools.wraps(f)
            def _record(*args, **kwargs):
                with cls(name_or_fn, **ctx_kwargs):
                    return f(*args, **kwargs)

            return _record

        return _wrapper
    else:
        if not inspect.isfunction(name_or_fn):
            raise ValueError(
                'Should directly apply the decorator to a function.')

        @functools.wraps(name_or_fn)
        def _record(*args, **kwargs):
            f = name_or_fn
            func_name = getattr(f, '__qualname__', f.__name__)
            module_name = getattr(f, '__module__', '')
            if module_name:
                full_name = f'{module_name}.{func_name}'
            else:
                full_name = func_name
            with cls(full_name, **ctx_kwargs):
                return f(*args, **kwargs)

        return _record


def get_user_hash(force_fresh_hash: bool = False) -> str:
    """Returns a unique user-machine specific hash as a user id.

    We cache the user hash in a file to avoid potential user_name or
    hostname changes causing a new user hash to be generated.

    Args:
        force_fresh_hash: Bypasses the cached hash in USER_HASH_FILE and the
            hash in the USER_ID_ENV_VAR and forces a fresh user-machine hash
            to be generated. Used by `kubernetes.ssh_key_secret_field_name` to
            avoid controllers sharing the same ssh key field name as the
            local client.
    """

    def _is_valid_user_hash(user_hash: Optional[str]) -> bool:
        if user_hash is None:
            return False
        try:
            int(user_hash, 16)
        except (TypeError, ValueError):
            return False
        return len(user_hash) == USER_HASH_LENGTH

    if not force_fresh_hash:
        user_hash = os.getenv(constants.USER_ID_ENV_VAR)
        if _is_valid_user_hash(user_hash):
            assert user_hash is not None
            return user_hash

    if not force_fresh_hash and os.path.exists(_USER_HASH_FILE):
        # Read from cached user hash file.
        with open(_USER_HASH_FILE, 'r', encoding='utf-8') as f:
            # Remove invalid characters.
            user_hash = f.read().strip()
        if _is_valid_user_hash(user_hash):
            return user_hash

    hash_str = user_and_hostname_hash()
    user_hash = hashlib.md5(hash_str.encode()).hexdigest()[:USER_HASH_LENGTH]
    if not _is_valid_user_hash(user_hash):
        # A fallback in case the hash is invalid.
        user_hash = uuid.uuid4().hex[:USER_HASH_LENGTH]
    os.makedirs(os.path.dirname(_USER_HASH_FILE), exist_ok=True)
    if not force_fresh_hash:
        # Do not cache to file if force_fresh_hash is True since the file may
        # be intentionally using a different hash, e.g. we want to keep the
        # user_hash for usage collection the same on the jobs/serve controller
        # as users' local client.
        with open(_USER_HASH_FILE, 'w', encoding='utf-8') as f:
            f.write(user_hash)
    return user_hash


def read_yaml_all(path: str) -> List[Dict[str, Any]]:
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load_all(f)
        configs = list(config)
        if not configs:
            # Empty YAML file.
            return [{}]
        return configs


def validate_schema(obj, schema, err_msg_prefix='', skip_none=True):
    """Validates an object against a given JSON schema.

    Args:
        obj: The object to validate.
        schema: The JSON schema against which to validate the object.
        err_msg_prefix: The string to prepend to the error message if
          validation fails.
        skip_none: If True, removes fields with value None from the object
          before validation. This is useful for objects that will never contain
          None because yaml.safe_load() loads empty fields as None.

    Raises:
        ValueError: if the object does not match the schema.
    """
    if skip_none:
        obj = {k: v for k, v in obj.items() if v is not None}
    err_msg = None
    try:
        validator.SchemaValidator(schema).validate(obj)
    except jsonschema.ValidationError as e:
        if e.validator == 'additionalProperties':
            if tuple(e.schema_path) == ('properties', 'envs',
                                        'additionalProperties'):
                # Hack. Here the error is Task.envs having some invalid keys. So
                # we should not print "unsupported field".
                #
                # This will print something like:
                # 'hello world' does not match any of the regexes: <regex>
                err_msg = (err_msg_prefix +
                           'The `envs` field contains invalid keys:\n' +
                           e.message)
            else:
                err_msg = err_msg_prefix
                assert isinstance(e.schema, dict), 'Schema must be a dictionary'
                known_fields = set(e.schema.get('properties', {}).keys())
                assert isinstance(e.instance,
                                  dict), 'Instance must be a dictionary'
                for field in e.instance:
                    if field not in known_fields:
                        most_similar_field = difflib.get_close_matches(
                            field, known_fields, 1)
                        if most_similar_field:
                            err_msg += (f'Instead of {field!r}, did you mean '
                                        f'{most_similar_field[0]!r}?')
                        else:
                            err_msg += f'Found unsupported field {field!r}.'
        else:
            message = e.message
            # Object in jsonschema is represented as dict in Python. Replace
            # 'object' with 'dict' for better readability.
            message = message.replace('type \'object\'', 'type \'dict\'')
            # Example e.json_path value: '$.resources'
            err_msg = (err_msg_prefix + message +
                       f'. Check problematic field(s): {e.json_path}')

    if err_msg:
        with ux_utils.print_exception_no_traceback():
            raise ValueError(err_msg)