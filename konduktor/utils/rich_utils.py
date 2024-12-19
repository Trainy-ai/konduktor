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

"""Rich status spinner utils."""
import contextlib
import threading
from typing import Union

import rich.console as rich_console

console = rich_console.Console(soft_wrap=True)
_status = None
_status_nesting_level = 0

_logging_lock = threading.RLock()


class _NoOpConsoleStatus:
    """An empty class for multi-threaded console.status."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def update(self, text):
        pass

    def stop(self):
        pass

    def start(self):
        pass


class _RevertibleStatus:
    """A wrapper for status that can revert to previous message after exit."""

    def __init__(self, message: str):
        if _status is not None:
            self.previous_message = _status.status
        else:
            self.previous_message = None
        self.message = message

    def __enter__(self):
        global _status_nesting_level
        _status.update(self.message)
        _status_nesting_level += 1
        _status.__enter__()
        return _status

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _status_nesting_level, _status
        _status_nesting_level -= 1
        if _status_nesting_level <= 0:
            _status_nesting_level = 0
            if _status is not None:
                _status.__exit__(exc_type, exc_val, exc_tb)
                _status = None
        else:
            _status.update(self.previous_message)

    def update(self, *args, **kwargs):
        _status.update(*args, **kwargs)

    def stop(self):
        _status.stop()

    def start(self):
        _status.start()


def safe_status(msg: str) -> Union['rich_console.Status', _NoOpConsoleStatus]:
    """A wrapper for multi-threaded console.status."""
    from konduktor import logging  # pylint: disable=import-outside-toplevel
    global _status
    if (threading.current_thread() is threading.main_thread() and
            not logging.is_silent()):
        if _status is None:
            _status = console.status(msg, refresh_per_second=8)
        return _RevertibleStatus(msg)
    return _NoOpConsoleStatus()