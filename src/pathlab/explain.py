"""Renderers for trace output: plain text, JSON, one-line verdicts."""

from __future__ import annotations

import json

from .algorithms import TraceResult


def render_text(result: TraceResult, max_steps: int | None = None) -> str:
    steps = result.steps
    if max_steps is not None:
        shown, hidden = steps[:max_steps], steps[max_steps:]
    else:
        shown, hidden = steps, []
    lines = [f"=== pathlab trace ({result.algo}) ===", result.summary(), ""]
    for s in shown:
        lines.append(f"{s.seq:>4} [{s.action:<9}] {s.text}")
    if hidden:
        lines.append(f"  ... {len(hidden)} more steps")
    return "\n".join(lines)


def render_json(result: TraceResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True)


def render_verdict(result: TraceResult) -> str:
    return result.summary()