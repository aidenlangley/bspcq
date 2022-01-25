#! /usr/bin/env python

from rich.tree import Tree
from typing import Any
import argparse
import json
import os
import rich
import subprocess


def setup_cli() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser(
        description="parses JSON output from 'bspc query' to provide a user \
            friendly visual representation of the BSP tree. See 'man bspc' for \
            more info. 'bspcq' can be used in a similar fashion to 'bspc \
            query', for example: 'bspcq -N -n 123456', or 'bspcq -N' for all \
            node BSP tree(s).",
    )

    argparser.add_argument(
        '-m', '--monitor', nargs='*', metavar='M',
        help="query for monitor(s), given an identifier. See 'man bspc' for \
            more information."
    )
    argparser.add_argument(
        '-d', '--desktop', nargs='*', metavar='D',
        help="query for desktop(s), given an identifier. See 'man bspc' for \
            more information."
    )
    argparser.add_argument(
        '-n', '--node', '-w', '--window', nargs='*', metavar='N',
        help="query for node(s), or window(s), given an identifier. See 'man \
            bspc' for more information."
    )

    argparser.add_argument(
        '-M', '--monitors', action='store_true',
        help="exclusively print the monitor node(s) of the BSP tree - excludes \
            all child nodes."
    )
    argparser.add_argument(
        '-D', '--desktops', action='store_true',
        help="exclusively print the desktop node(s) of the BSP tree - excludes \
            all child nodes."
    )
    argparser.add_argument(
        '-N', '--nodes', '-W', '--windows', action='store_true',
        help="exclusively print the node/window node(s) of the BSP tree."
    )

    argparser.add_argument(
        '-j', '--json', nargs='?', type=str, metavar='J',
        help="provide the data to be analyzed instead of letting 'bspcq' call \
            'bspc query'."
    )
    argparser.add_argument(
        '-s', '--simple', action='store_true',
        help="print a simplified view of the BSP tree."
    )

    return argparser.parse_args()


def run_cmd(cmd: list[str]) -> str:
    return subprocess.run(
        cmd, capture_output=True
    ).stdout.decode('utf-8').rstrip()


def get_node_info(bsp_tree: dict[str, Any]) -> dict[str, Any]:
    bsp_tree['xtitle'] = run_cmd(['xtitle', '{id}'.format(id=bsp_tree['id'])])
    return bsp_tree


def traverse_nodes(
    bsp_tree: dict[str, Any],
    nodes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """`bspwm` is simple, but it isn't easy. -zyk

    Probably the most complex piece of the puzzle - we repeatedly
    `recurse_nodes` here, since in theory we can have an infinite number of
    `node`s.
    """

    # Absence of `firstChild` means there is only a single active `node` on the
    # `desktop`, so we don't have to go fishing for children.
    if bsp_tree['firstChild'] is None:
        nodes.append(get_node_info(bsp_tree))

    else:
        if bsp_tree['firstChild'].get('client'):
            nodes.append(get_node_info(bsp_tree['firstChild']))

            # In the event that there is a `firstChild`, there will be a
            # `secondChild`. A `secondChild` can have a `firstChild`, and so on.
            traverse_nodes(bsp_tree['secondChild'], nodes)

        # A `firstChild` without a `client` is a branch without leaves - no
        # `node`s but there are more branches...
        else:
            traverse_nodes(bsp_tree['firstChild'], nodes)

    return nodes


def traverse_tree(iterable: list[Any] | dict[str, Any], tree: Tree) -> Tree:
    """Recursively iterate over a list or dict and populate a `Tree`."""

    def format_val(val: Any) -> str:
        if type(val) is str:
            return f"'[bold]{val}[/bold]'"

        else:
            return f'[bold]{val}[/bold]'

    if type(iterable) is dict:
        for key, val in iterable.items():

            if val is None:
                continue

            elif type(val) is dict or type(val) is list:
                if val.__len__() > 0:
                    traverse_tree(
                        val,
                        tree.add(f'[bold]{key}[/bold]')
                    )

            else:
                tree.add(f'[italic]{key}[/italic] {format_val(val)}')

    elif type(iterable) is list:
        for el in iterable:

            if el is None:
                continue

            elif type(el) is dict or type(el) is list:
                if el.__len__() > 0:
                    traverse_tree(el, tree)

            else:
                tree.add(format_val(el))

    return tree


def make_tree(label: str, bsp_tree: dict[str, Any], simple: bool) -> Tree:
    return Tree(label) if simple else traverse_tree(bsp_tree, Tree(label))


def analyze_monitor(
    bsp_tree: dict[str, Any],
    simple: bool
) -> tuple[dict[str, Any], Tree]:
    label = ' '.join([
        '[bold cyan]M[/bold cyan]:',
        '[bold]{id}[/bold]'.format(id=bsp_tree['id']),
        '{name}'.format(name=bsp_tree['name'])
    ])

    temp = bsp_tree.copy()
    temp['desktops'] = None

    return (bsp_tree['desktops'], make_tree(label, temp, simple))


def analyze_desktop(
    bsp_tree: dict[str, Any],
    simple: bool
) -> tuple[dict[str, Any], Tree]:
    label = ' '.join([
        '[bold green]D[/bold green]:',
        '[bold]{id}[/bold]'.format(id=bsp_tree['id']),
        '{name}'.format(name=bsp_tree['name'])
    ])

    temp = bsp_tree.copy()
    temp['root'] = None

    return (bsp_tree['root'], make_tree(label, temp, simple))


def analyze_nodes(
    bsp_tree: dict[str, Any],
    simple: bool
) -> tuple[list[dict[str, Any]], list[Tree]]:
    bsp_trees: list[dict[str, Any]] = []
    tree_list: list[Tree] = []

    for node in traverse_nodes(bsp_tree, []):
        label = ' '.join([
            '[bold yellow]N[/bold yellow]:',
            '[bold]{id}[/bold]'.format(id=node['id']),
            '{name}:'.format(name=node['client']['className']),
            '[italic]{xtitle}[/italic]'.format(
                xtitle=node['xtitle']
            )
        ])

        tree_list.append(make_tree(label, node, simple))
        bsp_trees.append(node)

    return (bsp_trees, tree_list)


def analyze_bsp_tree(
    bsp_tree: dict[str, Any],
    simple: bool
) -> Tree:
    tree = analyze_monitor(bsp_tree, simple)[1]

    desktop: dict[str, Any]
    for desktop in bsp_tree['desktops']:
        desktop_tree = tree.add(analyze_desktop(desktop, simple)[1])

        # Absence of a `root` means the desktop is not occupied by any `node`s.
        nodes: dict[str, Any] | None = desktop['root']
        if nodes is not None:

            for node_tree in analyze_nodes(nodes, simple)[1]:
                desktop_tree.add(node_tree)

    return tree


def bspc_query(
    domain: str,
    identifiers: list[Any] = []
) -> list[str]:
    cmd = ['bspc', 'query']

    bsp_trees: list[str] = []
    if domain == 'all':
        monitors_cmd = cmd.copy()
        monitors_cmd.extend(['-M'])

        monitors = run_cmd(monitors_cmd).split(os.linesep)
        for monitor in monitors:

            monitor_cmd = cmd.copy()
            monitor_cmd.extend(['-T', '-m', f'{monitor}'])
            bsp_trees.append(json.loads(run_cmd(monitor_cmd)))

    else:
        for identifier in identifiers:
            cmd.extend(['-T', f'--{domain}', identifier])
            bsp_trees.append(run_cmd(cmd))

    return bsp_trees


def bspcq() -> None:
    args: argparse.ArgumentParser = setup_cli()

    if args.json:
        return rich.print(analyze_bsp_tree(args.json, args.simple))

    # Determine how to run `bspc query` - the user will be able to pass multiple
    # optional arguments (`-n 123 -d 456`) but we will perform a `node` query in
    # as there is an order of preference.
    query: tuple[str, list[Any]]
    if args.monitor or args.desktop or args.node:
        if args.node:
            query = ('node', args.node)

        elif args.desktop:
            query = ('desktop', args.desktop)

        else:
            query = ('monitor', args.monitor)

        bsp_trees = bspc_query(query[0], query[1])

    else:
        bsp_trees = bspc_query('all')

    # These args provide behaviour constraints - the user may define the domain
    # that they are interested in, which means only information pertaining to
    # that domain will be output.
    if args.monitors:
        for tree in bsp_trees:
            rich.print(analyze_monitor(tree, args.simple)[1])

    if args.desktops:
        for tree in bsp_trees:
            desktops = analyze_monitor(tree, args.simple)[0]
            for desktop_tree in desktops:
                rich.print(analyze_desktop(desktop_tree, args.simple)[1])

    if args.nodes:
        if args.node:
            for tree in bsp_trees:
                for node_tree in analyze_nodes(tree, args.simple)[1]:
                    rich.print(node_tree)

        elif args.desktop:
            for tree in bsp_trees:

                nodes = analyze_desktop(tree, args.simple)[0]
                if nodes is not None:
                    for node_tree in analyze_nodes(nodes, args.simple)[1]:
                        rich.print(node_tree)

        else:
            for tree in bsp_trees:
                desktops = analyze_monitor(tree, args.simple)[0]
                for desktop_tree in desktops:

                    nodes = analyze_desktop(desktop_tree, args.simple)[0]
                    if nodes is not None:
                        for node_tree in analyze_nodes(nodes, args.simple)[1]:
                            rich.print(node_tree)

        return

    else:
        for bsp_tree in bsp_trees:
            full_tree = analyze_bsp_tree(bsp_tree, args.simple)
            rich.print(full_tree)

    return
