# Results

## Environment

- OS: Windows 11 (Git Bash), Python 3.14.3
- Network: **none used** — all demos ran against local example files
- Dependencies installed: **none** (standard library only)

## Validation performed

1. Syntax gate: `compileall`/AST parse over `src/pathlab/*.py` — clean.
2. Full test suite: `python -m unittest discover -s tests -t .`
3. Live demos of all four subcommands with exit codes recorded in `results/`.
4. Secret scan across source, tests, docs and results.

## Commands executed

```console
$ python -m unittest discover -s tests -t .
$ PYTHONPATH=src python -m pathlab trace examples/tiny.txt --algo dijkstra --start S --goal D
$ PYTHONPATH=src python -m pathlab trace examples/negative.txt --directed --algo bellman-ford --start S --goal C
$ PYTHONPATH=src python -m pathlab trace examples/negative_cycle.txt --directed --algo bellman-ford --start S --goal C
$ PYTHONPATH=src python -m pathlab trace examples/tiny.txt --algo floyd-warshall --start S --goal D
$ PYTHONPATH=src python -m pathlab viz examples/grid_small.txt --algo astar -o results/viz-grid-astar.html
$ PYTHONPATH=src python -m pathlab quiz examples/grid_small.txt --algo dijkstra --questions 5 < answers
$ PYTHONPATH=src python -m pathlab gen grid --rows 6 --cols 8 --density 0.3 --seed 9
```

## Observed result

### Tests

`Ran 105 tests in 4.4s — OK (exit 0)`. Coverage by area:

| Suite | Count | Focus |
|---|---|---|
| test_graph | 24 | loaders (edge/grid/JSON autodetect), validation errors, generator determinism & connectivity, save/load round trip |
| test_algorithms | 26 | textbook distances/path, step-stream invariants, unreachable, A\*≡Dijkstra, BF negatives & proof-round logic, FW≡Dijkstra over all pairs, step cap, negative diagonal |
| test_explain | 5 | text/JSON renderers, truncation, inf→null |
| test_viz | 7 | self-containment (exactly one `<script>`), payload, escaping, file bytes |
| test_quiz | 13 | question shape, determinism (same seed ⇒ same options), grading/threshold, answer parsing |
| test_cli | 30 | subprocess end-to-end: gen/trace/viz/quiz, exit codes 0/1/2, UTF-8 through pipes |

### Traces

- **Dijkstra** on `examples/tiny.txt`: `path S -> B -> D cost 15`,
  textbook distances A=7, B=9, C=20, D=15 (`results/trace-dijkstra-tiny.txt`, exit 0)
- **A\\* + manhattan** on the maze: cost 14, settles ≤ Dijkstra's node count
  (`results/trace-astar-grid.txt`, exit 0)
- **Bellman-Ford with negative edges**: `S=0, B=2, A=-1 (via S→B→A), C=0`,
  no false cycle (`results/trace-bf-negative.txt`, exit 0)
- **Bellman-Ford with negative cycle**:
  `NEGATIVE CYCLE: A -> B · note: negative cycle detected; distances are invalid`
  (`results/trace-bf-negcycle.txt`, exit 0 — detection is data, not a crash)
- **Floyd-Warshall** all-pairs on the textbook graph agrees with repeated
  Dijkstra for every source→target pair (asserted in tests)

### Visualizers (committed)

| File | Bytes | Content |
|---|---|---|
| `results/viz-grid-astar.html` | 34,332 | 51-step A\* crawl with the final path reveal |
| `results/viz-negcycle.html` | 15,059 | Bellman-Ford run + `NEGATIVE CYCLE: A -> B` |

Both files contain exactly one `<script>` tag, zero external references and
work from `file://`.

### Quiz grade boundaries

- correct answers fed → `score: 5/5 (100%) — PASS`, **exit 0**
  (`results/quiz-pass.txt`)
- invalid answers (`9`) → `score: 0/5 (0%) — FAIL`, **exit 1**
  (`results/quiz-fail.txt`)

### Generators

`gen grid --rows 6 --cols 8 --density 0.3 --seed 9` → valid JSON with S/T
markers (`results/generated-grid.json`); determinism and S↔T connectivity are
asserted in tests for other seeds too.

## Generated artifacts

`results/` — `trace-dijkstra-tiny.txt`, `trace-astar-grid.txt`,
`trace-bf-negative.txt`, `trace-bf-negcycle.txt`, `trace-fw-tiny.txt`,
`trace-bf-tiny.json`, `viz-grid-astar.html`, `viz-negcycle.html`, `viz.txt`,
`quiz-pass.txt`, `quiz-fail.txt`, `generated-grid.json`.

## Known limitations (honest accounting)

- Bellman-Ford clears `distances` to `{}` when a negative cycle exists —
  deliberately, since the values are mathematically meaningless there.
- Floyd-Warshall logs cap at 400 improvements (the final step notes how many
  were not logged); n > 40 triggers an explicit O(n³) warning in step 0.
- A\* on a coordinate-less graph silently falls back to the zero heuristic
  (reported in `note: heuristic: zero`); the direct `astar()` API still raises.
- Everything is single-process and in-memory; no file-watching or REPL mode.