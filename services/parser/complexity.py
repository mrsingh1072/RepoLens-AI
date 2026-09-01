"""Cyclomatic complexity estimation from syntax trees."""

from __future__ import annotations

from tree_sitter import Node

from services.parser.ts_utils import walk

# Node types that increment cyclomatic complexity by one.
_DECISION_TYPES = frozenset(
    {
        "if_statement",
        "elif_clause",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "except_clause",
        "catch_clause",
        "case_clause",
        "conditional_expression",
        "ternary_expression",
        "&&",
        "||",
        "boolean_operator",
        "binary_expression",  # counted when operator is && or ||
    }
)


def score_node(node: Node) -> int:
    """Estimate cyclomatic complexity for a subtree."""
    score = 1
    for child in walk(node):
        if child.type in _DECISION_TYPES:
            score += 1
            continue
        if child.type == "binary_expression" and child.child_count >= 3:
            op = child.children[1]
            if op.type in {"&&", "||"}:
                score += 1
    return score


def complexity_label(score: int) -> str:
    if score <= 5:
        return "low"
    if score <= 12:
        return "medium"
    return "high"


def file_complexity(root: Node) -> str:
    return complexity_label(score_node(root))
