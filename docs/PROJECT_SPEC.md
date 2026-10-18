# Project Spec — pathlab

## Summary

An offline graph path-algorithm learning lab (Python 3.10+, standard library
only) that traces four classic shortest-path algorithms step by step, renders
the trace as text/JSON/an animated self-contained HTML visualizer, and turns
the same traces into a scored prediction quiz.

Category: **algorithm-learning** (2nd use — `dpdrill` covered dynamic
programming table-filling on 2026-09-27; pathlab covers graph search, a
different family and interface).

## Problem

Shortest-path algorithms are usually learned by reading pseudocode. The gap
that hurts is seeing the *actual* order of decisions — which node settles,
which edge relaxes, why — on a graph you can hold in your head, and being
tested on predicting those decisions.

## Goals

1. **One step model for four algorithms.** Dijkstra, A\*, Bellman-Ford and
   Floyd-Warshall all emit `Step(action, text, node/edge, dist, settled,
   frontier)` records a renderer can replay.
2. **Honest semantics.** Early stop at the goal for Dijkstra/A\*, proof rounds
   only after n−1 rounds for Bellman-Ford (converging on round n−1 must NOT be
   called a negative cycle), Floyd-Warshall checks the `i == j` diagonal
   because that is where negative cycles become visible.
3. **Three renderings, one trace**: human text, machine JSON, animated SVG,
   plus a quiz — all derived from the same step list.
4. **Offline visualization.** The HTML file inlines its data, styles, script
   and SVG markers: it must work from `file://` with zero network requests.
5. **Deterministic everything.** Generators and quizzes are seeded; same seed
   → byte-identical graphs, options and shuffles.
6. **Exit codes as a contract**: quiz pass mark → exit 0/1, input errors → 2.

## Non-goals

- Not a general graph IDE (no editing, no layout algorithms beyond grid/chain).
- No Maximum-flow / MST / sorting-algorithm coverage in v1.
- No interactivity beyond the step scrubber (no "run your own edge weights"
  live editor).
- Not a web service; no server, no build step, no dependencies.

## Acceptance criteria

- `python -m unittest discover -s tests -t .` passes 100% from a clean clone.
- All four algorithms agree on the example graphs (asserted in tests).
- Generated maze: S guaranteed reachable from T (asserted by flood-fill).
- Quiz: 5 questions, deterministic at `--seed 11`; correct answers pass (exit
  0), wrong answers fail (exit 1) — both exercised end-to-end via stdin.
- `viz` output: exactly one `<script>` element, no `src=`/`@import`/`<link>`.
- Negative examples: `results/trace-bf-negcycle.txt` contains
  `NEGATIVE CYCLE: A -> B`; negative-but-acyclic example reports distances.

## Known limitations

- Floyd-Warshall is O(n³) (warned above 40 nodes in the first step).
- BF invalid distances after a negative cycle are intentionally cleared to `{}`.
- Grid cells are 4-connected with unit weights only.
- README comments in `.txt` examples use `#`; the edge-list tokenizer treats
  everything after `#` on a line as a comment (so weights must not contain `#`).