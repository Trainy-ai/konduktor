"""Batch job execution via k8s jobsets
https://jobset.sigs.k8s.io/
https://kueue.sigs.k8s.io/docs/tasks/run/jobsets/
"""

from typing import Dict, Optional

Path = str

from konduktor.backends import backend
from konduktor import logging

logger = logging.get_logger(__file__)

class JobsetBackend(backend.Backend):
    
    def _sync_file_mounts(
        self,
        all_file_mounts: Optional[Dict[Path, Path]],
        storage_mounts: Optional[Dict[Path, 'storage_lib.Storage']],
    ) -> None:
        logger.warning("i'm part of jobset backend. I'm not doing anything")
        pass
        # raise NotImplementedError