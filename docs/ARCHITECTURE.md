# Architecture — pathlab

## Module map

```
src/pathlab/
  graph.py        Graph model, loaders (edge list / grid / JSON), seeded generators
  algorithms.py   step-tracing Dijkstra, A*, Bellman-Ford, Floyd-Warshall + dispatcher
  explain.py      renderers: text, JSON, verdict line
  viz.py          self-contained HTML + SVG animation builder
  quiz.py         question builder (from the same step stream), grading, answer parsing
  cli.py          argparse subcommands: gen | trace | viz | quiz (exit codes 0/1/2)
  __main__.py     python -m pathlab
tests/            105 tests: loaders, algorithms, renderers, viz, quiz, CLI end-to-end
examples/         tiny.txt, grid_small.txt, negative.txt, negative_cycle.txt
```

## The step stream (the central contract)

```
Graph ──run_algorithm(algo)──> TraceResult
                                 ├─ steps: [Step]      ← single source of truth
                                 ├─ distances, settled, found, path, path_cost
                                 └─ negative_cycle | note
Step = { seq, action, text, node?, edge?, current?, dist{}, settled[], frontier[] }
```

Actions: `init · settle · relax · goal · no-path · improve · neg-cycle · done`.

Invariants (asserted by tests):

- `seq` is contiguous from 0; first step is `init`; last is `done` or `neg-cycle`.
- `settled ∩ frontier = ∅` and `settled` never shrinks during an Dijkstra/A\* run.
- `dist` snapshots omit `math.inf` and only contain graph node keys (for
  Floyd-Warshall the keys are `u->v` pairs — the visualizer detects this and
  hides per-node distance labels instead of guessing).

Quiz and visualizer both consume this stream; neither re-implements logic.

## Algorithm notes

| Algorithm | Decisions emitted | Correctness guardrails |
|---|---|---|
| Dijkstra | `settle` + `relax` per edge | lazy heap deletion (`if u in settled: continue`), early stop at goal |
| A\* | `settle` (shows g/h/f) + `relax` | admissible heuristic required; dispatcher falls back to `zero` when nodes lack coordinates; direct API stays strict (raises) |
| Bellman-Ford | `relax` tagged with round number | n−1 rounds; **then**, only if round 1..n−1 all changed, "proof rounds" run — a cycle is only reported when a proof round actually improves; cycle extracted by walking predecessor links n times then collecting the loop |
| Floyd-Warshall | `improve` per strict decrease | diagonal `i == j` is included so negative cycles appear; next-hop matrix for path reconstruction; log capped at 400 improvements with an explicit note |

Cross-algorithm consistency: one test runs all four over every example and
asserts the distance maps agree (Dijkstra ≡ Bellman-Ford ≡ A\* ≡ Floyd-Warshall
on non-negative graphs).

## Data flow by command

```
gen    graph.py generators ──(seeded)──> JSON on stdout or -o file
trace  load_graph -> run_algorithm -> render_text | render_json   (exit 0)
viz    load_graph -> run_algorithm -> build_html -> **one** .html   (exit 0)
quiz   load_graph -> build_questions(=run_algorithm + seeded picks)
                  -> stdin answers -> grade -> report          (exit 0 pass / 1 fail)
```

Errors (`GraphError`, `ValueError`, `OSError`) are caught in `cli.main` →
message on stderr → **exit 2**. argparse usage errors exit 2 as well.

## Visualizer

`viz.py` substitutes three placeholders into an HTML template: `__TITLE__`
(HTML-escaped), `__SUMMARY__` (HTML-escaped) and `__PAYLOAD__` (JSON with
`</` → `<\/` so graph ids cannot break out of the `<script>` element).

The page draws static geometry once (uniform scale into a 660×460 viewBox),
then `apply(i)` toggles classes — `settled`, `frontier`, `current`,
`active` edge — updates distance labels and reveals the final path polyline
on the last step. Controls: range scrubber, ⏮◀▶⏭ buttons, arrow/Home/End keys.

## Quiz

`build_questions` picks evenly spaced `settle`/`relax`/`improve` events,
captures the state *before* each event, corrects = the event's focus
(node / `u->v` edge / `u->v` pair), distractors come from the live frontier
first. One seeded `random.Random(seed)` per session → reproducible options.