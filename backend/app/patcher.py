"""Apply a model-generated, function-scoped patch without replacing surrounding code."""
from __future__ import annotations

import ast


def replace_function(source: str, replacement: str, target: str = 'allocate_hours') -> str:
    """Require exactly one top-level function, and preserve the rest of the program.

    This is a structural patch, not an arbitrary text search or executing a diff.
    """
    tree = ast.parse(source)
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == target]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one top-level {target} function')
    patch = ast.parse(replacement.strip())
    if len(patch.body) != 1 or not isinstance(patch.body[0], ast.FunctionDef) or patch.body[0].name != target:
        raise ValueError(f'Patch must contain only def {target}(...)')
    original = matches[0]
    revised = patch.body[0]
    if len(original.args.posonlyargs) != len(revised.args.posonlyargs) or \
       len(original.args.args) != len(revised.args.args):
        raise ValueError('Function patch must preserve positional parameter arity')
    lines = source.splitlines(keepends=True)
    # end_lineno includes the final physical line, and is available on Python 3.11+.
    updated = ''.join(lines[:original.lineno - 1]) + replacement.strip() + '\n\n' + ''.join(lines[original.end_lineno:])
    ast.parse(updated)
    return updated
