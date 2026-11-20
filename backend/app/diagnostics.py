"""Deterministic, auditable development-only diagnostics for repair prompts.

These hints are *not* proofs of a root cause. Code is never executed here.
"""
from __future__ import annotations

import ast
from collections import Counter
from difflib import unified_diff

from .models import CandidateResult


def error_summary(candidate: CandidateResult) -> dict[str, int]:
    """Collapse repeated errors by category rather than echoing hundreds of lines."""
    counts: Counter[str] = Counter()
    for seed in candidate.per_seed:
        for violation in seed.violations:
            if '不正または重複した科目' in violation:
                key = 'DUPLICATE_OR_UNKNOWN_SUBJECT'
            elif '利用可能時間と配分時間が一致しません' in violation:
                key = 'TOTAL_HOURS_MISMATCH'
            elif '時間数・上限の違反' in violation:
                key = 'INVALID_OR_EXCEEDED_HOURS'
            elif 'すべての科目を出力' in violation:
                key = 'MISSING_SUBJECT'
            elif '重複した生徒ID' in violation:
                key = 'DUPLICATE_STUDENT'
            elif '未出力の生徒' in violation:
                key = 'MISSING_STUDENT'
            elif 'Sandbox' in violation or seed.status == 'failed':
                key = 'EXECUTION_OR_OUTPUT_ERROR'
            else:
                key = 'OTHER_VALIDATION_ERROR'
            counts[key] += 1
    return dict(sorted(counts.items()))


def static_hints(source: str) -> list[str]:
    """Heuristic AST red flags for a second-stage repair; no semantic certainty."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ['Python AST could not be parsed; inspect source syntax first.']
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == 'append' and isinstance(node.func.value, ast.Name) and node.func.value.id == 'allocations':
                # Is this append inside a repeated allocation loop?
                for parent in ast.walk(tree):
                    if isinstance(parent, (ast.While, ast.For)) and node in ast.walk(parent):
                        findings.append(f'line {node.lineno}: allocations.append inside a loop; check duplicate subject output. Accumulate by subject and emit once.')
                        break
        if isinstance(node, (ast.AugAssign, ast.Assign)):
            targets = [node.target] if isinstance(node, ast.AugAssign) else node.targets
            for target in targets:
                if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant) and target.slice.value == 'max_hours':
                    findings.append(f'line {node.lineno}: max_hours appears on assignment LHS; verify input caps are never mutated.')
    return list(dict.fromkeys(findings))[:6]


def code_diff(before: str, after: str, *, max_chars: int = 12000) -> str:
    """Unified patch retained for inspection, truncated to protect API response size."""
    diff = ''.join(unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile='previous.py', tofile='revision.py', n=3,
    ))
    if len(diff) > max_chars:
        return diff[:max_chars] + '\n... [diff truncated; complete code saved separately]\n'
    return diff or '(no source change)'
