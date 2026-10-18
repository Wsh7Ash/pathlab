# pathlab

**Graph path-algorithm learning lab** — trace Dijkstra, A\*, Bellman-Ford and
Floyd-Warshall step by step, export a self-contained HTML visualizer, and drill
with a seeded prediction quiz. Standard library only, 100% offline.

```console
$ python -m pathlab trace examples/tiny.txt --algo dijkstra --start S --goal D

=== pathlab trace (dijkstra) ===
dijkstra S -> D: 41 steps · path S -> B -> D cost 15 · note: 12 heap pops

   0 [init     ] start at S with distance 0; everything else is ∞
   1 [settle   ] settle S: distance 0 is now permanent (frontier had nothing)
   2 [relax    ] relax S -> A: ∞ -> 7 through edge weight 7
   3 [relax    ] relax S -> B: ∞ -> 9 through edge weight 9
   4 [settle   ] settle A: distance 7 is now permanent (frontier had B)
  ...
```

Open the visualizer it can emit — one HTML file, no network, no CDN:

```console
$ python -m pathlab viz examples/grid_small.txt --algo astar -o plan.html
wrote plan.html (34332 bytes, 51 steps)
astar 0,0 -> 6,8: 51 steps · path ... cost 14 · note: heuristic: manhattan
```

Then quiz yourself on what the algorithm does next:

```console
$ python -m pathlab quiz examples/grid_small.txt --algo dijkstra --questions 5
Q1. After step 4 (relax), which node settles next?
  settled:  0,0, 0,1
  frontier: 0,1, 1,0
  dist:     0,1=1, 1,0=1
  1) 1,0   2) 0,3   3) 0,2   4) 1,4
...
score: 4/5 (80%) — PASS
```

## Why

Reading an algorithm description is not the same as predicting its next move.
pathlab makes every decision auditable: each `relax`, `settle` and `improve`
event is a numbered step with a human explanation and a full distance/frontier
snapshot, replayable in text, JSON, an animated SVG, or a quiz.

## Four ways to use it

| Command | What it does |
|---|---|
| `pathlab trace` | step-by-step log (`text` or `json`) for any of the 4 algorithms |
| `pathlab viz` | one self-contained HTML file with a step scrubber + SVG graph |
| `pathlab quiz` | prediction quiz with score threshold (`--pass`, exit 0/1) |
| `pathlab gen` | seeded random grids and weighted graphs to learn on |

## Algorithms

- **Dijkstra** — non-negative weights, early stop at the goal, heap-pop count.
- **A\*** — `manhattan` / `euclidean` / `zero` heuristics, steps show g/h/f;
  falls back to the zero heuristic automatically for graphs without coordinates.
- **Bellman-Ford** — negative edges, convergence detection, and **reachable
  negative-cycle detection** with the cycle extracted via predecessor links.
- **Floyd-Warshall** — all-pairs, every pivot improvement logged (capped at 400
  with a note), negative cycle surfaces as a negative diagonal.

All four run behind one dispatcher and agree with each other: the test suite
asserts Dijkstra == Bellman-Ford == A\* == Floyd-Warshall on every example.

## Input formats

- **Edge list**: `A B 4` (`#` comments, `--directed`, negative weights OK)
- **Grid**: `#` wall, `.` open, `S` start, `T` goal — 4-connected unit weights
- **JSON**: `{"nodes": [{"id":"A","x":0,"y":0}], "edges": [{"from":"A","to":"B","w":3}]}`

Auto-detected; `--input-format` forces one.

## Quick start

```console
$ git clone https://github.com/Wsh7Ash/pathlab && cd pathlab
$ PYTHONPATH=src python -m pathlab --help
$ python -m unittest discover -s tests -t .     # 105 tests
$ python -m pathlab gen grid --rows 12 --cols 16 --seed 3 -o maze.json
$ PYTHONPATH=src python -m pathlab viz maze.json -o maze.html
```

(Or `pip install -e .` to get a `pathlab` console script.)

## Documentation

- [docs/PROJECT_SPEC.md](docs/PROJECT_SPEC.md) — requirements and scope
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — modules and step model
- [docs/USAGE.md](docs/USAGE.md) — full command reference
- [RESULTS.md](RESULTS.md) — validation evidence
- [SECURITY.md](SECURITY.md) — safe-use notes

## Requirements

Python **≥ 3.10**, standard library only.

## License

MIT — see [LICENSE](LICENSE).