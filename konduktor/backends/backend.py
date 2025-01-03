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

"""Konduktor backend interface."""
from typing import Dict, Optional

import konduktor
from konduktor.utils import ux_utils

Path = str

class Backend:
    """Backend interface: handles provisioning, setup, and scheduling."""

    # NAME is used to identify the backend class from cli/yaml.
    NAME = 'backend'

    # --- APIs ---
    def check_resources_fit_cluster(self, task: 'konduktor.Task') -> bool:
        """Check whether resources of the task are satisfied by cluster."""
        raise NotImplementedError

    def sync_workdir(self, workdir: Path) -> None:
        return self._sync_workdir(handle, workdir)

    def sync_file_mounts(
        self,
        all_file_mounts: Optional[Dict[Path, Path]],
        storage_mounts: Optional[Dict[Path, 'storage_lib.Storage']],
    ) -> None:
        return self._sync_file_mounts(all_file_mounts, storage_mounts)

    def add_storage_objects(self, task: 'konduktor.Task') -> None:
        raise NotImplementedError

    def execute(self,
                task: 'konduktor.Task',
                detach_run: bool,
                dryrun: bool = False) -> Optional[int]:
        """Execute the task on the cluster.

        Returns:
            Job id if the task is submitted to the cluster, None otherwise.
        """
        ux_utils.spinner_message('Submitting job')
        return self._execute(task, detach_run, dryrun)

    def post_execute(self) -> None:
        """Post execute(): e.g., print helpful inspection messages."""
        return self._post_execute(handle, down)

    def register_info(self, **kwargs) -> None:
        """Register backend-specific information."""
        pass

    def _sync_workdir(self, workdir: Path) -> None:
        raise NotImplementedError

    def _sync_file_mounts(
        self,
        all_file_mounts: Optional[Dict[Path, Path]],
        storage_mounts: Optional[Dict[Path, 'storage_lib.Storage']],
    ) -> None:
        raise NotImplementedError


    def _execute(self,
                 task: 'konduktor.Task',
                 detach_run: bool,
                 dryrun: bool = False) -> Optional[int]:
        raise NotImplementedError
