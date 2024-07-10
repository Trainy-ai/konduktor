import click

from konduktor.controller import node as node_control


@click.group()
def main():
    """konduktor cli"""
    pass


@main.command()
def reset() -> None:
    """Removes taints from all nodes"""
    nodes = node_control.list_nodes()
    for node in nodes:
        node_control.untaint(node)
