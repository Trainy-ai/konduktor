# Copyright 2024 SkyPilot Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# The modifications are proprietary and subject to the terms of the Trainy Software License Version 1.0
# Copyright 2024 Trainy Inc.

"""The konduktor CLI

In addition we'll have a command so people can access
the observability dashboard

konduktor dashboard <CLUSTER_NAME>

"""

import click
import os
import posthog
from typing import Dict, List, Optional, Tuple

from konduktor.controller import node as node_control


class _DocumentedCodeCommand(click.Command):
    """Corrects help strings for documented commands such that --help displays
    properly and code blocks are rendered in the official web documentation.
    """

    def get_help(self, ctx):
        help_str = ctx.command.help
        ctx.command.help = help_str.replace('.. code-block:: bash\n', '\b')
        return super().get_help(ctx)

@click.group()
def main():
    """konduktor cli"""
    pass


@main.command('reset', cls=_DocumentedCodeCommand)
def reset() -> None:
    """Removes taints from all nodes"""
    nodes = node_control.list_nodes()
    for node in nodes:
        node_control.untaint(node)


@main.command('auth', cls=_DocumentedCodeCommand)
def auth() -> None:
    """Renews Bearer token"""
    pass


@main.command('status', cls=_DocumentedCodeCommand)
def status() -> None:
    """List available clusters and running jobs"""
    pass

