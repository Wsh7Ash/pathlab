"""Step-tracing implementations of four classic path algorithms.

Every algorithm produces :class:`Step` records — an action, a human-readable
explanation and snapshots of distances / settled set / frontier — so the
visualizer and the quiz can replay a run deterministically. Distance snapshots
omit ``math.inf`` entries to keep JSON output compact.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from .graph import Graph

INF = math.inf

ALGORITHMS = ("dijkstra", "astar", "bellman-ford", "floyd-warshall")


# -- shared types -----------------------------------------------------------


@dataclass
class Step:
    seq: int
    action: str       # init|settle|relax|goal|no-path|improve|neg-cycle|done
    text: str
    node: str | None = None
    edge: tuple[str, str] | None = None
    current: str | None = None
    dist: dict[str, float] = field(default_factory=dict)
    settled: list[str] = field(default_factory=list)
    frontier: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "seq": self.seq, "action": self.action, "text": self.text,
            "node": self.node, "edge": list(self.edge) if self.edge else None,
            "current": self.current,
            "dist": {k: _jsonable(v) for k, v in self.dist.items()},
            "settled": list(self.settled), "frontier": list(self.frontier),
        }


@dataclass
class TraceResult:
    algo: str
    start: str | None
    goal: str | None
    steps: list[Step]
    distances: dict[str, float]        # node -> cost ("u->v" keys for FW)
    settled: list[str]
    found: bool
    path: list[str] | None
    path_cost: float | None
    negative_cycle: list[str] | None = None
    note: str | None = None

    def summary(self) -> str:
        if self.algo == "floyd-warshall":
            head = "floyd-warshall all-pairs"
        else:
            head = f"{self.algo} {self.start}" + (
                f" -> {self.goal}" if self.goal else "")
        parts = [f"{head}: {len(self.steps)} steps"]
        if self.negative_cycle:
            parts.append("NEGATIVE CYCLE: " + " -> ".join(self.negative_cycle))
        elif self.goal is not None:
            parts.append(
                f"path {' -> '.join(self.path)} cost {self.path_cost:g}"
                if self.found else "no path")
        if self.note:
            parts.append(f"note: {self.note}")
        return " · ".join(parts)

    def to_dict(self) -> dict:
        return {
            "algo": self.algo, "start": self.start, "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "distances": {k: _jsonable(v) for k, v in self.distances.items()},
            "settled": list(self.settled), "found": self.found,
            "path": list(self.path) if self.path else None,
            "path_cost": _jsonable(self.path_cost),
            "negative_cycle": list(self.negative_cycle) if self.negative_cycle else None,
            "note": self.note,
        }


def _jsonable(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


class _Recorder:
    """Collects steps. ``dist`` is a dict, or a callable computing one
    (Floyd-Warshall rebuilds its flat "u->v" snapshot on every step)."""

    def __init__(self, dist):
        self.steps: list[Step] = []
        self._seq = 0
        self._dist = dist

    def _snapshot(self) -> dict[str, float]:
        source = self._dist() if callable(self._dist) else self._dist
        return {k: v for k, v in source.items() if v != INF}

    def add(self, action: str, text: str, *, node=None, edge=None, current=None,
            settled=(), frontier=()) -> Step:
        step = Step(
            seq=self._seq, action=action, text=text, node=node, edge=edge,
            current=current, dist=self._snapshot(),
            settled=sorted(set(settled)), frontier=sorted(set(frontier)),
        )
        self.steps.append(step)
        self._seq += 1
        return step


# -- helpers ---------------------------------------------------------------


def _check(g: Graph, start: str | None, goal: str | None) -> tuple[str, str | None]:
    if start is None:
        raise ValueError("start node is required (use --start or a file with S)")
    if not g.has_node(start):
        raise ValueError(f"start {start!r} not in graph")
    if goal is not None and not g.has_node(goal):
        raise ValueError(f"goal {goal!r} not in graph")
    return start, goal


def _reconstruct(prev: dict[str, str | None], goal: str) -> list[str]:
    path = [goal]
    node = goal
    while prev.get(node) is not None:
        node = prev[node]  # type: ignore[assignment]
        path.append(node)
    path.reverse()
    return path


def _frontier(dist: dict[str, float], settled: set[str]) -> list[str]:
    return [n for n in sorted(dist) if n not in settled]


# -- Dijkstra ---------------------------------------------------------------


def dijkstra(g: Graph, start: str, goal: str | None = None) -> TraceResult:
    start, goal = _check(g, start, goal)
    dist: dict[str, float] = {start: 0.0}
    prev: dict[str, str | None] = {start: None}
    settled: set[str] = set()
    rec = _Recorder(dist)
    heap: list[tuple[float, str]] = [(0.0, start)]
    rec.add("init", f"start at {start} with distance 0; everything else is ∞",
            node=start, current=start, settled=settled, frontier=[start])

    pops = 0
    while heap:
        d, u = heapq.heappop(heap)
        pops += 1
        if u in settled:
            continue
        settled.add(u)
        fr = _frontier(dist, settled)
        rec.add("settle", (f"settle {u}: distance {d:g} is now permanent "
                           f"(frontier had {', '.join(fr) or 'nothing'})"),
                node=u, current=u, settled=settled, frontier=fr)
        if goal is not None and u == goal:
            rec.add("goal", f"goal {goal} reached at cost {d:g} — stop early",
                    node=u, current=u, settled=settled, frontier=fr)
            break
        for v, w in sorted(g.neighbors(u)):
            nd = d + w
            if nd < dist.get(v, INF):
                old = dist.get(v, INF)
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
                old_s = "∞" if old == INF else f"{old:g}"
                rec.add("relax", (f"relax {u} -> {v}: {old_s} -> {nd:g} "
                                  f"through edge weight {w:g}"),
                        node=v, edge=(u, v), current=u, settled=settled,
                        frontier=_frontier(dist, settled))

    found = goal is not None and goal in settled
    if goal is not None and not found:
        rec.add("no-path", f"frontier exhausted — {goal} is unreachable from {start}",
                settled=settled, frontier=_frontier(dist, settled))
    rec.add("done", f"finished: {len(settled)} of {len(g.nodes)} nodes settled",
            settled=settled, frontier=_frontier(dist, settled))
    return TraceResult(
        algo="dijkstra", start=start, goal=goal, steps=rec.steps,
        distances={k: v for k, v in dist.items() if v != INF},
        settled=sorted(settled), found=found,
        path=_reconstruct(prev, goal) if found and goal else None,
        path_cost=dist.get(goal, INF) if found and goal else None,
        note=f"{pops} heap pops",
    )


# -- A* ---------------------------------------------------------------------


def _make_heuristic(g: Graph, goal: str, kind: str):
    pos = g.positions
    if kind == "zero":
        return lambda _n: 0.0
    if goal not in pos:
        raise ValueError(f"heuristic {kind!r} needs node positions; "
                         "use --heuristic zero for unpositioned graphs")
    gx, gy = pos[goal]
    if kind == "manhattan":
        return lambda n: (abs(pos.get(n, (gx, gy))[0] - gx)
                          + abs(pos.get(n, (gx, gy))[1] - gy))
    if kind == "euclidean":
        return lambda n: math.dist(pos.get(n, (gx, gy)), (gx, gy))
    raise ValueError(f"unknown heuristic: {kind} (use manhattan|euclidean|zero)")


def astar(g: Graph, start: str, goal: str | None = None,
          heuristic: str = "manhattan") -> TraceResult:
    if goal is None:
        raise ValueError("A* requires a goal (use --goal or a file with T)")
    start, goal = _check(g, start, goal)
    h = _make_heuristic(g, goal, heuristic)
    gdist: dict[str, float] = {start: 0.0}
    prev: dict[str, str | None] = {start: None}
    settled: set[str] = set()
    rec = _Recorder(gdist)
    f0 = h(start)
    rec.add("init", (f"start at {start}: g=0, h={f0:g}, f={f0:g} "
                     f"({heuristic} heuristic)"),
            node=start, current=start, settled=settled, frontier=[start])

    heap: list[tuple[float, float, str]] = [(f0, 0.0, start)]
    while heap:
        _f, d, u = heapq.heappop(heap)
        if u in settled:
            continue
        settled.add(u)
        fr = _frontier(gdist, settled)
        rec.add("settle", (f"settle {u}: g={d:g}, h={h(u):g}, f={d + h(u):g} "
                           f"is minimal (frontier had {', '.join(fr) or 'nothing'})"),
                node=u, current=u, settled=settled, frontier=fr)
        if u == goal:
            rec.add("goal", f"goal {goal} reached at cost {d:g} — stop early",
                    node=u, current=u, settled=settled, frontier=fr)
            break
        for v, w in sorted(g.neighbors(u)):
            nd = d + w
            if nd < gdist.get(v, INF):
                old = gdist.get(v, INF)
                gdist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd + h(v), nd, v))
                old_s = "∞" if old == INF else f"{old:g}"
                rec.add("relax", (f"relax {u} -> {v}: g {old_s} -> {nd:g} "
                                  f"(f={nd + h(v):g}) via weight {w:g}"),
                        node=v, edge=(u, v), current=u, settled=settled,
                        frontier=_frontier(gdist, settled))

    found = goal in settled
    if not found:
        rec.add("no-path", f"frontier exhausted — {goal} is unreachable",
                settled=settled, frontier=_frontier(gdist, settled))
    rec.add("done", f"finished: {len(settled)} of {len(g.nodes)} nodes settled",
            settled=settled, frontier=_frontier(gdist, settled))
    return TraceResult(
        algo="astar", start=start, goal=goal, steps=rec.steps,
        distances={k: v for k, v in gdist.items() if v != INF},
        settled=sorted(settled), found=found,
        path=_reconstruct(prev, goal) if found else None,
        path_cost=gdist.get(goal, INF) if found else None,
        note=f"heuristic: {heuristic}",
    )


# -- Bellman-Ford -----------------------------------------------------------


def bellman_ford(g: Graph, start: str, goal: str | None = None) -> TraceResult:
    start, goal = _check(g, start, goal)
    dist: dict[str, float] = {start: 0.0}
    prev: dict[str, str | None] = {start: None}
    arcs = g.arcs()
    n = len(g.nodes)
    rec = _Recorder(dist)
    rec.add("init", (f"start at {start} with distance 0; will relax all "
                     f"{len(arcs)} arcs up to {n - 1} times"),
            node=start, frontier=sorted(dist))

    def relax_round(label: str) -> tuple[bool, bool, str | None]:
        """One sweep over all arcs. Returns (changed, improved(v), victim)."""
        changed = False
        improved = False
        victim: str | None = None
        for u, v, w in arcs:
            du = dist.get(u, INF)
            if du == INF:
                continue
            nd = du + w
            if nd < dist.get(v, INF):
                old = dist.get(v, INF)
                dist[v] = nd
                prev[v] = u
                changed = True
                improved = True
                victim = v
                old_s = "∞" if old == INF else f"{old:g}"
                rec.add("relax", (f"{label}: relax {u} -> {v}: {old_s} -> "
                                  f"{nd:g} (weight {w:g})"),
                        node=v, edge=(u, v), frontier=sorted(dist))
        return changed, improved, victim

    converged = False
    for round_no in range(1, max(n, 2)):
        changed, _, _ = relax_round(f"round {round_no}")
        if not changed:
            converged = True
            rec.add("done", f"no improvement in round {round_no} — converged early",
                    frontier=sorted(dist))
            break

    # Only a still-improving extra sweep proves a reachable negative cycle.
    negative = False
    victim: str | None = None
    if not converged:
        for extra in range(1, n + 1):
            _, improved, v = relax_round(f"proof round {extra}")
            if improved:
                negative = True
                victim = v
    if not converged and not negative:
        rec.add("done", f"finished after {n - 1} rounds — no more improvements",
                frontier=sorted(dist))

    cycle: list[str] | None = None
    if negative:
        cycle = _extract_cycle(prev, victim, n) if victim else None
        rec.add("neg-cycle", ("negative cycle: "
                              + (" -> ".join(cycle + cycle[:1]) if cycle else "?")),
                node=cycle[0] if cycle else None, frontier=sorted(dist))

    found = False
    path = None
    if not negative and goal is not None and goal in dist:
        found = True
        path = _reconstruct(prev, goal)
    return TraceResult(
        algo="bellman-ford", start=start, goal=goal, steps=rec.steps,
        distances={} if negative else
        {k: v for k, v in dist.items() if v != INF},
        settled=[], found=found, path=path,
        path_cost=dist.get(goal, INF) if found and goal else None,
        negative_cycle=cycle if negative else None,
        note=("negative cycle detected; distances are invalid" if negative
              else "handles negative edge weights"),
    )


def _extract_cycle(prev: dict[str, str | None], victim: str,
                   n: int) -> list[str] | None:
    """Walk predecessors from a late-updating node; lands inside the cycle."""
    node: str | None = victim
    for _ in range(max(n, 1) + 1):
        if node is None:
            return None
        node = prev.get(node)
    if node is None:
        return None
    cycle = [node]
    cur = prev.get(node)
    while cur is not None and cur != node and len(cycle) <= n + 1:
        cycle.append(cur)
        cur = prev.get(cur)
    if cur is None:      # walked off the chain: no closed loop after all
        return None
    cycle.reverse()
    return cycle


# -- Floyd-Warshall ---------------------------------------------------------


def floyd_warshall(g: Graph, start: str | None = None,
                    goal: str | None = None) -> TraceResult:
    nodes = g.nodes
    n = len(nodes)
    idx = {node: i for i, node in enumerate(nodes)}
    d = [[INF] * n for _ in range(n)]
    nxt: list[list[str | None]] = [[None] * n for _ in range(n)]
    for i in range(n):
        d[i][i] = 0.0
    for u in nodes:
        for v, w in g.neighbors(u):
            i, j = idx[u], idx[v]
            if w < d[i][j]:
                d[i][j] = w
                nxt[i][j] = v

    def flat() -> dict[str, float]:
        out: dict[str, float] = {}
        for i in range(n):
            for j in range(n):
                if i != j and d[i][j] != INF:
                    out[f"{nodes[i]}->{nodes[j]}"] = d[i][j]
        return out

    rec = _Recorder(flat)   # callable: snapshot rebuilt on every step
    init_text = f"initialize {n}x{n} matrix: direct edges loaded, diagonal 0"
    if n > 40:
        init_text += f"  [warning: O(n^3) with n={n}]"
    rec.add("init", init_text, frontier=sorted(flat()))

    cap = 400        # keep step logs readable on bigger graphs
    recorded = 0
    suppressed = 0
    for k in range(n):
        for i in range(n):
            for j in range(n):
                # NB: i == j is included on purpose — a negative diagonal is
                # exactly how a negative cycle becomes visible
                if d[i][k] == INF or d[k][j] == INF:
                    continue
                nd = d[i][k] + d[k][j]
                if nd < d[i][j]:
                    old = d[i][j]
                    d[i][j] = nd
                    nxt[i][j] = nxt[i][k]
                    if recorded < cap:
                        rec.add("improve",
                                f"via {nodes[k]}: {nodes[i]} -> {nodes[j]} "
                                f"{old:g} -> {nd:g}",
                                edge=(nodes[i], nodes[j]),
                                frontier=sorted(flat()))
                        recorded += 1
                    else:
                        suppressed += 1

    neg = [nodes[i] for i in range(n) if d[i][i] < 0]
    if neg:
        last = rec.add("neg-cycle", "negative cycle through: " + ", ".join(neg),
                       node=neg[0], frontier=sorted(flat()))
    else:
        last = rec.add("done", f"finished all {n} pivot phases",
                       frontier=sorted(flat()))
    if suppressed:
        last.text += f" · {suppressed} further improvements not logged"

    found = False
    path: list[str] | None = None
    cost: float | None = None
    if start is not None and goal is not None:
        if not g.has_node(start):
            raise ValueError(f"start {start!r} not in graph")
        if not g.has_node(goal):
            raise ValueError(f"goal {goal!r} not in graph")
        if not neg:
            i, j = idx[start], idx[goal]
            if d[i][j] != INF:
                cur = start
                chain = [cur]
                while cur != goal and len(chain) <= n:
                    cur = nxt[idx[cur]][j]  # type: ignore[assignment]
                    if cur is None:
                        break
                    chain.append(cur)
                if chain[-1] == goal:
                    found = True
                    path = chain
                    cost = d[i][j]

    return TraceResult(
        algo="floyd-warshall", start=start, goal=goal, steps=rec.steps,
        distances=flat(), settled=[], found=found, path=path, path_cost=cost,
        negative_cycle=neg or None,
        note=("negative cycle found" if neg else "all-pairs distances"),
    )


# -- dispatch ---------------------------------------------------------------


def run_algorithm(g: Graph, algo: str, start: str | None = None,
                  goal: str | None = None, **opts) -> TraceResult:
    if algo not in ALGORITHMS:
        raise ValueError(
            f"unknown algorithm: {algo} (choose from {', '.join(ALGORITHMS)})")
    s = start if start is not None else g.start
    t = goal if goal is not None else g.goal
    if algo == "dijkstra":
        return dijkstra(g, s, t)
    if algo == "astar":
        heuristic = opts.get("heuristic", "manhattan")
        anchor = t if t is not None else s
        if heuristic != "zero" and anchor is not None and anchor not in g.positions:
            # graphs without coordinates cannot support a geometric heuristic;
            # fall back to Dijkstra-compatible behavior instead of failing
            heuristic = "zero"
        return astar(g, s, t, heuristic=heuristic)
    if algo == "bellman-ford":
        return bellman_ford(g, s, t)
    return floyd_warshall(g, s, t)