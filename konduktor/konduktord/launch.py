import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from konduktor import logging as konduktor_logging
from konduktor.konduktord import constants

logger = konduktor_logging.init_logger("konduktord")

class LogFileHandler(FileSystemEventHandler):
    """
    Log file processor to find CUDA or NCCL Errors
    uses inotify to detect fs events under logging
    folders to enqueue processing created/modified
    logs
    """

    def __init__(self):

        self.files_map = {}

    def on_modified(self, event):
        self.process(event.src_path)

    def on_created(self, event):
        self.process(event.src_path)

    def process(self, file_path):
        """
        Reads the latest set of logs
        handles log rotation so if current log
        gets rotated, finish reading it and continue
        onto the newly minted log file.
        """
        # Get file stats
        file_stat = os.stat(file_path)
        current_inode = file_stat.st_ino

        # Check if the file is already being tracked
        if file_path in self.files_map:
            last_inode = self.files_map[file_path]["inode"]
            if last_inode != current_inode:
                # File rotation detected
                # Read the rest of the old file
                # and open the new one
                self.read_lines(self.files_map[file_path]["file"])
                self.files_map[file_path]["file"].close()
                self.files_map[file_path] = {"inode": current_inode, "position": 0, "file": open(file_path, 'r')}
            else:
                # Continue reading the current file
                self.read_lines(file_path)
        else:
            # New file detected
            self.files_map[file_path] = {"inode": current_inode, "position": 0, "file": open(file_path, 'r')}
            self.read_lines(file_path)

    def read_lines(self, file_path):
        file_info = self.files_map[file_path]
        file = file_info["file"]
        file.seek(file_info["position"])
        lines = file.readlines()
        file_info["position"] = file.tell()
        for line in lines:
            self.process_log_entry(line.strip())

    def process_log_entry(self, log_entry):
        # Process the log entry (e.g., print it or do something else)
        print(log_entry)

if __name__ == "__main__":
    paths = os.environ["WATCHED_DIRS"].split(",")
    for path in paths:
        logger.info(f"watching {path}")
        event_handler = LogFileHandler()
        observer = Observer()
        observer.schedule(event_handler, path, recursive=True)
        observer.start()

    while True:
        time.sleep(constants.EVENT_CHECKING_INTERVAL_SECONDS)
