"""Compare lexical caller search and a bounded Python AST index on synthetic source."""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import symtable
import sys
import time


FIXTURE = Path(__file__).resolve().parents[1] / 'tests/enhancement/fixtures/symbol_index'
FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)
NESTED_SCOPE = FUNCTION + (ast.ClassDef, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
EXPECTED = {
    'units::convert': {'pipeline.py:7', 'pipeline.py:11'},
    'units::clamp': {'pipeline.py:15'},
}


def scope_nodes(body):
    for node in body:
        yield node
        if isinstance(node, NESTED_SCOPE):
            continue
        yield from scope_nodes(ast.iter_child_nodes(node))


def imports(node):
    if isinstance(node, ast.Import):
        return [(item.asname or item.name.split('.')[0], (item.name, None)) for item in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [(item.asname or item.name, (node.module, item.name)) for item in node.names]
    return []


def imported_bindings(tree, scope):
    candidates = []
    counts = Counter(name for node in scope_nodes(tree.body) for name, _ in imports(node))
    if any(isinstance(node, ast.ImportFrom) and any(item.name == '*' for item in node.names)
           for node in scope_nodes(tree.body)):
        return {}
    for node in tree.body:
        candidates.extend((name, target) for name, target in imports(node) if name != '*')
    return {name: target for name, target in candidates
            if counts[name] == 1 and not scope.lookup(name).is_assigned()}


def local_functions(tree):
    bindings = Counter()
    for node in scope_nodes(tree.body):
        if isinstance(node, FUNCTION + (ast.ClassDef,)):
            bindings[node.name] += 1
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bindings[node.id] += 1
        bindings.update(name for name, _ in imports(node))
    return {node.name for node in tree.body if isinstance(node, FUNCTION) and bindings[node.name] == 1}


def index_edges(files):
    """Resolve cross-module calls through top-level imports in flat Python source."""
    trees = {path.stem: ast.parse(source, filename=path.name) for path, source in files.items()}
    definitions = {module: local_functions(tree) for module, tree in trees.items()}
    edges = []
    for path, source in files.items():
        tree = trees[path.stem]
        scope = symtable.symtable(source, path.name, 'exec')
        bindings = imported_bindings(tree, scope)
        function_scopes = {(table.get_name(), table.get_lineno()): table for table in scope.get_children()}
        for node in tree.body:
            if not isinstance(node, FUNCTION):
                continue
            local = function_scopes[node.name, node.lineno]
            for call in scope_nodes(node.body):
                if not isinstance(call, ast.Call):
                    continue
                callee = call.func
                if isinstance(callee, ast.Name):
                    name, attribute = callee.id, None
                elif isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name):
                    name, attribute = callee.value.id, callee.attr
                else:
                    continue
                if name not in bindings:
                    continue
                symbol_scope = local.lookup(name)
                if not symbol_scope.is_global() or symbol_scope.is_assigned():
                    continue
                module, member = bindings[name]
                if member is None:
                    member = attribute
                elif attribute is not None:
                    continue
                if member in definitions.get(module, ()):
                    edges.append((path.name, call.lineno, node.name, f'{module}::{member}'))
    return sorted(set(edges))


def lexical_sites(root, targets, rg):
    sites = {}
    context_bytes = 0
    for target in targets:
        symbol = target.split('::')[1]
        command = [rg, '--no-config', '--line-number', '--with-filename', '--no-heading',
                   '--color', 'never', '--glob', '*.py', '--', rf'\b{re.escape(symbol)}\s*\(', '.']
        result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=10)
        if result.returncode not in (0, 1):
            raise ValueError('ripgrep caller search failed')
        context_bytes += len(result.stdout.encode('utf-8'))
        sites[target] = set()
        for line in result.stdout.splitlines():
            name, number, code = line.split(':', 2)
            if not re.match(r'\s*(?:(?:async\s+)?def|class)\s+', code):
                sites[target].add(f'{Path(name).name}:{number}')
    return sites, context_bytes


def indexed_sites(root, targets):
    files = {path: path.read_text(encoding='utf-8') for path in sorted(root.glob('*.py'))}
    edges = [edge for edge in index_edges(files) if edge[3] in targets]
    return ({target: {f'{file}:{line}' for file, line, _, edge in edges if edge == target} for target in targets},
            sum(len(f'{file}:{line}::{caller} -> {target}\n'.encode('utf-8')) for file, line, caller, target in edges))


def compare(root, rg, repeats):
    methods = {'lexical_rg': lambda: lexical_sites(root, EXPECTED, rg),
               'import_aware_ast': lambda: indexed_sites(root, EXPECTED)}
    elapsed = {name: [] for name in methods}
    observations = {}
    for repeat in range(repeats):
        order = list(methods) if repeat % 2 == 0 else list(reversed(methods))
        for method in order:
            start = time.perf_counter()
            result = methods[method]()
            elapsed[method].append(time.perf_counter() - start)
            if method in observations and observations[method] != result:
                raise ValueError('benchmark observations varied across repeats')
            observations[method] = result
    report = {}
    for method, (sites, context) in observations.items():
        rows = {target: {'matches': sorted(sites[target] & expected),
                         'missing': sorted(expected - sites[target]), 'extra': sorted(sites[target] - expected)}
                for target, expected in EXPECTED.items()}
        report[method] = {'cases': rows, 'context_bytes': context,
                          'median_ms': round(1000 * statistics.median(elapsed[method]), 3)}
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rg', default='rg')
    parser.add_argument('--repeats', type=int, default=9)
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error('repeats must be positive')
    try:
        fixture = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(FIXTURE.glob('*.py'))}
        print(json.dumps({'fixture_sha256': fixture, 'repeats': args.repeats,
                          'results': compare(FIXTURE, args.rg, args.repeats)}, indent=2))
    except (OSError, ValueError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print(f'Symbol index comparison blocked: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
