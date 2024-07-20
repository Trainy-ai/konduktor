"""
Controller loop
The controller is run as a deployment and repeatedly polls the logging backend
for GPU related error logs. When a GPU, CUDA, NCCL error is detected,
we check against a set of known patterns(regexes) to see if the error is
irrecoverable making the node unfit for more work. We can then label/taint
the node to prevent more pods from being scheduled onto the node.

Sometimes an NCCL error can be raised due to all-reduce style workloads causing
all workers to fail even though only one is actually faulty. To place workers,
back into the working pool, we run a health check which just consists of doing NCCL
test on the tainted nodes
"""

import time
from typing import Set

from konduktor import logging
from konduktor.controller import constants, parse
from konduktor.controller import node as node_control

KONDUKTOR_CONTROLLER_LOG_POLL_SECONDS = 5
KONDUKTOR_CONTROLLER_HEALTH_CHECK_FREQ = 5

logger = logging.get_logger("konduktor.controller")


def main():
    logger.info(
        f"starting konduktor.controller ver. {constants.KONDUKTOR_CONTROLLER_VERSION}"
    )
    while True:
        for _ in range(KONDUKTOR_CONTROLLER_HEALTH_CHECK_FREQ):
            time.sleep(KONDUKTOR_CONTROLLER_LOG_POLL_SECONDS)
            error_by_pod: Set[str] = parse.pod_errors()
            error_by_dmesg: Set[str] = parse.dmesg_errors()
            for node in error_by_pod | error_by_dmesg:
                node_control.taint(node)

        node_control.health_check()


if __name__ == "__main__":
    main()
