# Usage — pathlab

```
pathlab gen grid  [--rows N] [--cols N] [--density F] [--seed N] [-o FILE]
pathlab gen graph [--nodes N] [--edges N] [--directed] [--weight-max N] [--seed N] [-o FILE]
pathlab trace FILE [--algo A] [--start N] [--goal N] [--format text|json] [--max-steps K]
pathlab viz   FILE [--algo A] [--start N] [--goal N] [-o OUT.html]
pathlab quiz  FILE [--algo A] [--start N] [--goal N] [--questions K] [--seed N]
                [--options K] [--pass PCT]
```

Common flags on `trace`/`viz`/`quiz`:

| Flag | Default | Meaning |
|---|---|---|
| `--algo` | `dijkstra` | `dijkstra` \| `astar` \| `bellman-ford` \| `floyd-warshall` |
| `--start` | `S` in file | start node |
| `--goal` | `T` in file | goal node (required semantics for A\*) |
| `--input-format` | `auto` | `edge` \| `grid` \| `json` |
| `--directed` | off | read an edge list as directed arcs |
| `--heuristic` | `manhattan` | A\*: `manhattan` \| `euclidean` \| `zero` |

Exit codes: **0** success (quiz ≥ `--pass`), **1** quiz below the pass mark,
**2** usage or input error.

## Input formats

**Edge list** (`examples/tiny.txt`):

```
S A 7        # weight defaults to 1
S B 9
```

**Grid** (`examples/grid_small.txt`) — `#` wall, `.`/`+` open, `S`/`T`
markers, 4-connected unit weights, nodes named `row,col`:

```
S...#....
.#...#..#
```

**JSON** — coordinates for positioned layouts:

```json
{"directed": false,
 "nodes": [{"id": "A", "x": 0, "y": 0}],
 "edges": [{"from": "A", "to": "B", "w": 3}],
 "start": "A", "goal": "B"}
```

## trace

```console
$ pathlab trace examples/tiny.txt --algo dijkstra --start S --goal D
$ pathlab trace examples/negative.txt --directed --algo bellman-ford \
    --start S --goal C --format json
$ pathlab trace examples/grid_small.txt --algo bellman-ford --max-steps 20
```

Text output starts with a verdict line:

```
dijkstra S -> D: 41 steps · path S -> B -> D cost 15 · note: 12 heap pops
bellman-ford S -> C: 18 steps · NEGATIVE CYCLE: A -> B · note: distances are invalid
floyd-warshall all-pairs: 51 steps · path S -> ... -> D cost 15 · note: all-pairs distances
```

`--format json` emits `{algo, start, goal, steps[], distances, settled,
found, path, path_cost, negative_cycle, note}` (`inf` distances become `null`).

## viz

```console
$ pathlab viz examples/grid_small.txt --algo astar -o plan.html
wrote plan.html (34332 bytes, 51 steps)
```

Open the file directly — everything is inlined. The scrubber (or arrow keys)
steps through the run; green = settled, dashed amber = frontier, red ring =
current node, the amber bar highlights the edge being relaxed; distance labels
update per step; the path polyline appears on the final step.

## quiz

```console
$ pathlab quiz examples/grid_small.txt --algo dijkstra --questions 5 --pass 80
```

Questions are drawn evenly from the algorithm's decision points:

- `dijkstra`/`astar` → *which node settles next?*
- `bellman-ford` → *which edge relaxes next?*
- `floyd-warshall` → *which pair improves next?*

Answer with the option number (`1..4`), a letter (`a..d`), or the exact node/
edge label. Unparseable input counts as wrong. `--seed` fixes both question
selection and option order; `--pass` sets the exit-0 threshold (default 70).

## gen

```console
$ pathlab gen grid --rows 12 --cols 16 --density 0.3 --seed 7 -o maze.json
wrote maze.json: 154 nodes, 187 edges (S=0,0, T=11,15)

$ pathlab gen graph --nodes 12 --seed 3
```

Guarantees: same seed → byte-identical output; generated grids always have a
reachable `S`→`T`; generated undirected graphs are always connected; generated
graphs carry `start`/`goal` markers so downstream commands work with no flags.

## Ideas for practice

1. Trace Dijkstra on `examples/tiny.txt`, predict every `settle` before
   reading the next line, then run the quiz with `--pass 100`.
2. Compare A\*'s settle count against Dijkstra's on the same grid.
3. Watch why Bellman-Ford needs proof rounds: trace
   `examples/negative_cycle.txt` and find the first `proof round` improvement.
4. Feed `examples/negative.txt` to Dijkstra anyway (it does not support
   negative weights) and note why Bellman-Ford is the right tool.