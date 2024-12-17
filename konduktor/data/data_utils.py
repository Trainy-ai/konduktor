"""
"""
import concurrent.futures
from enum import Enum
from multiprocessing import pool
import os
import re
import subprocess
import textwrap
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse

from filelock import FileLock

from konduktor import logging

Client = Any

logger = logging.get_logger(__name__)


def split_gcs_path(gcs_path: str) -> Tuple[str, str]:
    """Splits GCS Path into Bucket name and Relative Path to Bucket

    Args:
      gcs_path: str; GCS Path, e.g. gcs://imagenet/train/
    """
    path_parts = gcs_path.replace('gs://', '').split('/')
    bucket = path_parts.pop(0)
    key = '/'.join(path_parts)
    return bucket, key


def verify_gcs_bucket(name: str) -> bool:
    """Helper method that checks if the GCS bucket exists

    Args:
      name: str; Name of GCS Bucket (without gs:// prefix)
    """
    try:
        gcp.storage_client().get_bucket(name)
        return True
    except gcp.not_found_exception():
        return False


def is_cloud_store_url(url):
    result = urllib.parse.urlsplit(url)
    # '' means non-cloud URLs.
    return result.netloc


def _group_files_by_dir(
        source_list: List[str]) -> Tuple[Dict[str, List[str]], List[str]]:
    """Groups a list of paths based on their directory

    Given a list of paths, generates a dict of {dir_name: List[file_name]}
    which groups files with same dir, and a list of dirs in the source_list.

    This is used to optimize uploads by reducing the number of calls to rsync.
    E.g., ['a/b/c.txt', 'a/b/d.txt', 'a/e.txt'] will be grouped into
    {'a/b': ['c.txt', 'd.txt'], 'a': ['e.txt']}, and these three files can be
    uploaded in two rsync calls instead of three.

    Args:
        source_list: List[str]; List of paths to group
    """
    grouped_files: Dict[str, List[str]] = {}
    dirs = []
    for source in source_list:
        source = os.path.abspath(os.path.expanduser(source))
        if os.path.isdir(source):
            dirs.append(source)
        else:
            base_path = os.path.dirname(source)
            file_name = os.path.basename(source)
            if base_path not in grouped_files:
                grouped_files[base_path] = []
            grouped_files[base_path].append(file_name)
    return grouped_files, dirs


def parallel_upload(source_path_list: List[str],
                    filesync_command_generator: Callable[[str, List[str]], str],
                    dirsync_command_generator: Callable[[str, str], str],
                    bucket_name: str,
                    access_denied_message: str,
                    create_dirs: bool = False,
                    max_concurrent_uploads: Optional[int] = None) -> None:
    """Helper function to run parallel uploads for a list of paths.

    Used by Store to run rsync commands in parallel by
    providing appropriate command generators.

    Args:
        source_path_list: List of paths to local files or directories
        filesync_command_generator: Callable that generates rsync command
            for a list of files belonging to the same dir.
        dirsync_command_generator: Callable that generates rsync command
            for a directory.
        access_denied_message: Message to intercept from the underlying
            upload utility when permissions are insufficient. Used in
            exception handling.
        create_dirs: If the local_path is a directory and this is set to
            False, the contents of the directory are directly uploaded to
            root of the bucket. If the local_path is a directory and this is
            set to True, the directory is created in the bucket root and
            contents are uploaded to it.
        max_concurrent_uploads: Maximum number of concurrent threads to use
            to upload files.
    """
    # Generate gsutil rsync command for files and dirs
    commands = []
    grouped_files, dirs = _group_files_by_dir(source_path_list)
    # Generate file upload commands
    for dir_path, file_names in grouped_files.items():
        sync_command = filesync_command_generator(dir_path, file_names)
        commands.append(sync_command)
    # Generate dir upload commands
    for dir_path in dirs:
        if create_dirs:
            dest_dir_name = os.path.basename(dir_path)
        else:
            dest_dir_name = ''
        sync_command = dirsync_command_generator(dir_path, dest_dir_name)
        commands.append(sync_command)

    # Run commands in parallel
    with pool.ThreadPool(processes=max_concurrent_uploads) as p:
        p.starmap(
            run_upload_cli,
            zip(commands, [access_denied_message] * len(commands),
                [bucket_name] * len(commands)))


def get_gsutil_command() -> Tuple[str, str]:
    """Gets the alias'd command for gsutil and a command to define the alias.

    This is required for applying platform-specific flags to gsutil.

    In particular, we disable multiprocessing on Mac using
    `-o "GSUtil:parallel_process_count=1"`. Multithreading is still enabled.
    gsutil on Mac has a bug with multiprocessing that causes it to crash
    when uploading files. Related issues:
    https://bugs.python.org/issue33725
    https://github.com/GoogleCloudPlatform/gsutil/issues/464

    The flags are added by checking the platform using bash in a one-liner.
    The platform check is done inline to have the flags match where the command
    is executed, rather than where the code is run. This is important when
    the command is run in a remote VM.

    Returns:
        Tuple[str, str] : (gsutil_alias, command to generate the alias)
        The command to generate alias must be run before using the alias. E.g.,
        ```
        gsutil_alias, alias_gen = get_gsutil_command()
        cmd_to_run = f'{alias_gen}; {gsutil_alias} cp ...'
        ```
    """
    gsutil_alias = 'skypilot_gsutil'
    disable_multiprocessing_flag = '-o "GSUtil:parallel_process_count=1"'

    # Define skypilot_gsutil as a shell function instead of an alias.
    # This function will behave just like alias, but can be called immediately
    # after its definition on the same line
    alias_gen = (f'[[ "$(uname)" == "Darwin" ]] && {gsutil_alias}() {{ '
                 f'gsutil -m {disable_multiprocessing_flag} "$@"; }} '
                 f'|| {gsutil_alias}() {{ gsutil -m "$@"; }}')

    return gsutil_alias, alias_gen


def run_upload_cli(command: str, access_denied_message: str, bucket_name: str):
    # TODO(zhwu): Use log_lib.run_with_log() and redirect the output
    # to a log file.
    with subprocess.Popen(command,
                          stderr=subprocess.PIPE,
                          stdout=subprocess.DEVNULL,
                          shell=True) as process:
        stderr = []
        assert process.stderr is not None  # for mypy
        while True:
            line = process.stderr.readline()
            if not line:
                break
            str_line = line.decode('utf-8')
            stderr.append(str_line)
            if access_denied_message in str_line:
                process.kill()
                with ux_utils.print_exception_no_traceback():
                    raise PermissionError(
                        'Failed to upload files to '
                        'the remote bucket. The bucket does not have '
                        'write permissions. It is possible that '
                        'the bucket is public.')
        returncode = process.wait()
        if returncode != 0:
            stderr_str = '\n'.join(stderr)
            with ux_utils.print_exception_no_traceback():
                logger.error(stderr_str)
                raise exceptions.StorageUploadError(
                    f'Upload to bucket failed for store {bucket_name}. '
                    'Please check the logs.')
