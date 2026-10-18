# Changelog

All notable changes to pathlab are documented here.

## 1.0.0 — 2026-10-17

Initial release.

### Added

- **Graph model** with three input formats: edge list (comments, `--directed`,
  negative weights), grid (`#`/`.`/`S`/`T`, 4-connected), JSON (coordinates,
  strict node declaration), all auto-detected.
- **Seeded generators**: `gen grid` (S↔T connectivity guaranteed), `gen graph`
  (connected when undirected, carries start/goal markers).
- **Four step-tracing algorithms** behind one dispatcher:
  - Dijkstra (lazy heap deletion, early stop at goal, heap-pop note)
  - A\* (manhattan/euclidean/zero; steps show g/h/f; zero-heuristic fallback
    for coordinate-less graphs via the dispatcher, strict in the direct API)
  - Bellman-Ford (round tags, early convergence, proof-round negative-cycle
    detection with predecessor-link cycle extraction)
  - Floyd-Warshall (pivot improvements logged, 400-step cap with a note,
    negative diagonal detection, next-hop path reconstruction)
- **Renderers**: text trace with truncation, JSON (finite distances only,
  `inf` → `null`), one-line verdict summaries.
- **Self-contained HTML visualizer**: inline SVG, step scrubber, keyboard
  navigation, settled/frontier/current highlighting, distance labels, final
  path reveal, script-breakout-safe payload embedding.
- **Prediction quiz**: node/edge/pair questions derived from real decision
  points, seeded option shuffling, number/letter/label answer input, `--pass`
  threshold mapped to exit codes.
- Test suite: **105 tests** (`unittest`), including cross-algorithm agreement
  checks, CLI subprocess end-to-end, and viz self-containment assertions.
- CI workflow (Python 3.10/3.12/3.14), docs (`PROJECT_SPEC`, `ARCHITECTURE`,
  `USAGE`, `SECURITY`), MIT license, example graphs in `examples/`.