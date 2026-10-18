# Contributing to pathlab

Thanks for helping improve pathlab.

## Development

```console
$ python -m unittest discover -s tests -t .    # 105 tests, no dependencies
$ python -m pathlab --help
```

Python ≥ 3.10, **standard library only** — please keep it that way. Style:
4-space indent, type hints on public functions, `from __future__ import
annotations`, docstrings on modules and public API.

## Where things live

| Area | File(s) | Notes |
|---|---|---|
| Loaders/generators | `graph.py` | `GraphError` for all input problems |
| Algorithms | `algorithms.py` | the step stream is a contract — see ARCHITECTURE |
| Renderers | `explain.py`, `viz.py` | both consume `TraceResult` only |
| Quiz | `quiz.py` | never re-implements algorithm logic |
| CLI | `cli.py` | exit codes 0/1/2 are public API |

## Guidelines

- Tests accompany every change: loaders/algorithms get unit tests; anything
  touching exit codes gets a CLI subprocess test.
- If you touch algorithm semantics, add a cross-check test (your algorithm vs
  Dijkstra on an existing example) — that is how Bellman-Ford's proof-round
  logic stays honest.
- Determinism is a feature: no `random` without a seed, no wall-clock in
  outputs, no iteration order dependence on `dict` insertion from user input
  (nodes are sorted).
- Update `results/` evidence and `docs/USAGE.md` when adding flags.

## Commits

Small, described-by-purpose commits; reference issues where they exist.