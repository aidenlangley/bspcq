from argparse import ArgumentParser
from json import loads
from os import linesep
from rich import print
from rich.tree import Tree
from subprocess import run as run_sys
from typing import Any, Dict, List, Tuple


def config() -> ArgumentParser:
    argparser = ArgumentParser(
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

    return argparser


def run() -> None:
    args: ArgumentParser = config().parse_args()

    if args.json:
        return print(analyze_bsp_tree(args.json, args.simple))

    # Determine how to run `bspc query` - the user will be able to pass multiple
    # optional arguments (`-n 123 -d 456`) but we will perform a `node` query in
    # as there is an order of preference.
    query: Tuple[str, List[Any]]
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
            print(analyze_monitor(tree, args.simple)[1])

        return

    if args.desktops:
        for tree in bsp_trees:
            desktops = analyze_monitor(tree, args.simple)[0]
            for desktop_tree in desktops:
                print(analyze_desktop(desktop_tree, args.simple)[1])

        return

    if args.nodes:
        if args.node:
            for tree in bsp_trees:
                for node_tree in analyze_nodes(tree, args.simple)[1]:
                    print(node_tree)

            return

        elif args.desktop:
            for tree in bsp_trees:

                nodes = analyze_desktop(tree, args.simple)[0]
                if nodes is not None:
                    for node_tree in analyze_nodes(nodes, args.simple)[1]:
                        print(node_tree)

            return

        else:
            for tree in bsp_trees:
                desktops = analyze_monitor(tree, args.simple)[0]
                for desktop_tree in desktops:

                    nodes = analyze_desktop(desktop_tree, args.simple)[0]
                    if nodes is not None:
                        for node_tree in analyze_nodes(nodes, args.simple)[1]:
                            print(node_tree)

            return

    else:
        for bsp_tree in bsp_trees:
            full_tree = analyze_bsp_tree(bsp_tree, args.simple)
            print(full_tree)

    return


def bspc_query(
    domain: str,
    identifiers: List[Any] = []
) -> List[str]:
    cmd = ['bspc', 'query']

    bsp_trees: List[str] = []
    if domain == 'all':
        monitors_cmd = cmd.copy()
        monitors_cmd.extend(['-M'])

        monitors = run_cmd(monitors_cmd).split(linesep)
        for monitor in monitors:

            monitor_cmd = cmd.copy()
            monitor_cmd.extend(['-T', '-m', f'{monitor}'])
            bsp_trees.append(loads(run_cmd(monitor_cmd)))

    else:
        for identifier in identifiers:
            cmd.extend(['-T', f'--{domain}', identifier])

            try:
                bsp_trees.append(loads(run_cmd(cmd)))
            except:
                print('`' + ' '.join(cmd) + '` returned no results.')


    return bsp_trees


def run_cmd(cmd: List[str]) -> str:
    return run_sys(cmd, capture_output=True).stdout.decode('utf-8').rstrip()


def analyze_bsp_tree(
    bsp_tree: Dict[str, Any],
    simple: bool
) -> Tree:
    # If `desktops` exists, we loop through each.
    if bsp_tree.get('desktops'):
        tree = analyze_monitor(bsp_tree, simple)[1]

        desktop: Dict[str, Any]
        for desktop in bsp_tree['desktops']:
            desktop_tree = tree.add(analyze_desktop(desktop, simple)[1])

            # Absence of a `root` means the desktop is not occupied by any `node`s.
            nodes: dict[str, Any] | None = desktop['root']
            if nodes is not None:

                for node_tree in analyze_nodes(nodes, simple)[1]:
                    desktop_tree.add(node_tree)

    # Otherwise, we're only dealing with a single desktop.
    else:
        tree = Tree(bsp_tree['name']).add(analyze_desktop(bsp_tree, simple)[1])

        # Absence of a `root` means the desktop is not occupied by any `node`s.
        nodes: dict[str, Any] | None = bsp_tree['root']
        if nodes is not None:

            for node_tree in analyze_nodes(nodes, simple)[1]:
                tree.add(node_tree)

    return tree


def analyze_monitor(
    bsp_tree: Dict[str, Any],
    simple: bool
) -> Tuple[Dict[str, Any], Tree]:
    label = ' '.join([
        '[bold cyan]M[/bold cyan]:',
        '[bold]{id}[/bold]'.format(id=bsp_tree['id']),
        '{name}'.format(name=bsp_tree['name'])
    ])

    temp = bsp_tree.copy()
    temp['desktops'] = None

    return (
        bsp_tree['desktops'] if bsp_tree.get('desktops') else bsp_tree,
        make_tree(label, temp, simple)
    )


def analyze_desktop(
    bsp_tree: Dict[str, Any],
    simple: bool
) -> Tuple[Dict[str, Any], Tree]:
    label = ' '.join([
        '[bold green]D[/bold green]:',
        '[bold]{id}[/bold]'.format(id=bsp_tree['id']),
        '{name}'.format(name=bsp_tree['name'])
    ])

    temp = bsp_tree.copy()
    temp['root'] = None

    return (bsp_tree['root'], make_tree(label, temp, simple))


def analyze_nodes(
    bsp_tree: Dict[str, Any],
    simple: bool
) -> Tuple[List[Dict[str, Any]], List[Tree]]:
    bsp_trees: List[Dict[str, Any]] = []
    tree_list: List[Tree] = []

    for node in traverse_nodes(bsp_tree, []):
        # If a client exists, we've got an occupied node - if we don't, we've
        # got a receptable.
        client = node.get('client')
        name = client['className'] if client else 'receptacle'

        label = ' '.join([
            '[bold yellow]N[/bold yellow]:',
            '[bold]{id}[/bold]'.format(id=node['id']),
            '{name}'.format(name=name),
            '[italic]{xtitle}[/italic]'.format(
                xtitle=node['xtitle']
            )
        ])

        tree_list.append(make_tree(label, node, simple))
        bsp_trees.append(node)

    return (bsp_trees, tree_list)


def traverse_nodes(
    bsp_tree: Dict[str, Any],
    nodes: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """`bspwm` is simple, but it isn't easy. -zyk

    Probably the most complex piece of the puzzle - we repeatedly
    `recurse_nodes` here, since in theory we can have an infinite number of
    `node`s.
    """

    # Absence of `firstChild` means there is only a single active `node` on the
    # `desktop`, so we don't have to go fishing for children.
    if bsp_tree['firstChild'] is None:

        bsp_tree['xtitle'] = run_cmd([
            'xtitle',
            '{id}'.format(id=bsp_tree['id'])
        ])
        nodes.append(bsp_tree)

    else:
        if bsp_tree['firstChild'].get('client'):
            bsp_tree['firstChild']['xtitle'] = run_cmd([
                'xtitle',
                '{id}'.format(id=bsp_tree['firstChild']['id'])
            ])
            nodes.append(bsp_tree['firstChild'])

            # In the event that there is a `firstChild`, there will be a
            # `secondChild`. A `secondChild` can have a `firstChild`, and so on.
            traverse_nodes(bsp_tree['secondChild'], nodes)

        # A `firstChild` without a `client` is a branch without leaves - no
        # `node`s but there are more branches...
        else:
            traverse_nodes(bsp_tree['firstChild'], nodes)

    return nodes


def traverse_tree(iterable: List[Any] | Dict[str, Any], tree: Tree) -> Tree:
    """Recursively iterate over a List or Dict and populate a `Tree`."""

    def format_val(val: Any) -> str:
        return f"'[bold]{val}[/bold]'"

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


def make_tree(label: str, bsp_tree: Dict[str, Any], simple: bool) -> Tree:
    return Tree(label) if simple else traverse_tree(bsp_tree, Tree(label))
