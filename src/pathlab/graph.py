"""Graph model plus loaders (edge list / grid / JSON) and seeded generators.

Input formats
-------------
Edge list (``--format edge``)::

    # comments (full-line or trailing) are ignored
    A B 4
    B C 1.5      # weight defaults to 1

Grid (``--format grid``), one character per cell:

    S..#
    .#.T
    #...

    '#' wall, '.'/'+' open, 'S' start, 'T' goal
    nodes are 4-connected with unit weights and identified as "row,col"

JSON (``--format json``)::

    {"directed": false,
     "nodes": [{"id": "A", "x": 0.1, "y": 0.2}],
     "edges": [{"from": "A", "to": "B", "w": 3}],
     "start": "A", "goal": "B"}
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field

GRID_CHARS = set("#.+ST")
OPEN_CHARS = set(".+ST")


class GraphError(ValueError):
    """Raised for malformed graph input."""


@dataclass
class Graph:
    directed: bool = False
    adjacency: dict[str, list[tuple[str, float]]] = field(default_factory=dict)
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    start: str | None = None
    goal: str | None = None
    meta: dict = field(default_factory=dict)

    # -- construction -----------------------------------------------------

    def add_node(self, node: str, pos: tuple[float, float] | None = None) -> None:
        self.adjacency.setdefault(node, [])
        if pos is not None:
            self.positions[node] = (float(pos[0]), float(pos[1]))

    def add_edge(self, a: str, b: str, weight: float = 1.0) -> None:
        if a == b:
            raise GraphError(f"self-loop not allowed: {a}")
        w = float(weight)
        if not math.isfinite(w):
            raise GraphError(f"edge weight must be finite: {a} -{w}-> {b}")
        self.add_node(a)
        self.add_node(b)
        self.adjacency[a].append((b, w))
        if not self.directed:
            self.adjacency[b].append((a, w))

    # -- inspection -------------------------------------------------------

    @property
    def nodes(self) -> list[str]:
        return sorted(self.adjacency)

    def has_node(self, node: str) -> bool:
        return node in self.adjacency

    def neighbors(self, node: str) -> list[tuple[str, float]]:
        return self.adjacency.get(node, [])

    def arcs(self) -> list[tuple[str, str, float]]:
        """Every directed arc (undirected edges appear in both directions)."""
        out: list[tuple[str, str, float]] = []
        for u in self.nodes:
            for v, w in self.adjacency[u]:
                out.append((u, v, w))
        return out

    def edges(self) -> list[tuple[str, str, float]]:
        """Unique edges for drawing: one entry per undirected pair."""
        seen: set = set()
        out: list[tuple[str, str, float]] = []
        for u, v, w in self.arcs():
            key = (u, v) if self.directed else tuple(sorted((u, v)))
            if key in seen:
                continue
            seen.add(key)
            out.append((u, v, w))
        return out

    def weight(self, a: str, b: str) -> float:
        for v, w in self.adjacency.get(a, []):
            if v == b:
                return w
        raise GraphError(f"no edge {a} -> {b}")

    def to_dict(self) -> dict:
        return {
            "directed": self.directed,
            "nodes": [
                {"id": n,
                 "x": self.positions.get(n, (0.0, 0.0))[0],
                 "y": self.positions.get(n, (0.0, 0.0))[1]}
                for n in self.nodes
            ],
            "edges": [
                {"from": u, "to": v, "w": w} for (u, v, w) in self.edges()
            ],
            "start": self.start,
            "goal": self.goal,
            "meta": self.meta,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


# -- loaders ---------------------------------------------------------------


def _parse_edge_list(text: str, directed: bool) -> Graph:
    g = Graph(directed=directed)
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) not in (2, 3):
            raise GraphError(
                f"line {lineno}: expected 'FROM TO [WEIGHT]', got {raw.strip()!r}")
        a, b = parts[0], parts[1]
        try:
            w = float(parts[2]) if len(parts) == 3 else 1.0
        except ValueError:
            raise GraphError(f"line {lineno}: bad weight {parts[2]!r}") from None
        g.add_edge(a, b, w)   # add_edge validates finiteness and self-loops
    if not g.adjacency:
        raise GraphError("edge list contains no edges")
    return g


def _looks_like_grid(lines: list[str]) -> bool:
    if not lines or not lines[0]:
        return False
    width = len(lines[0])
    if any(len(line) != width for line in lines):
        return False
    if any(ch not in GRID_CHARS for line in lines for ch in line):
        return False
    # a real grid marker must be present, otherwise it is just short words
    return any(ch in "ST" for line in lines for ch in line)


def _parse_grid(text: str) -> Graph:
    rows = [line for line in text.splitlines() if line.strip() != ""]
    if not rows:
        raise GraphError("grid is empty")
    if any(len(r) != len(rows[0]) for r in rows):
        raise GraphError("grid rows have inconsistent lengths")
    bad = sorted({ch for r in rows for ch in r} - GRID_CHARS)
    if bad:
        raise GraphError(f"unsupported grid characters: {bad}")

    g = Graph(directed=False,
              meta={"kind": "grid", "rows": len(rows), "cols": len(rows[0])})
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                continue
            nid = f"{r},{c}"
            g.add_node(nid, pos=(float(c), float(r)))
            if ch == "S" and g.start is None:
                g.start = nid
            elif ch == "T" and g.goal is None:
                g.goal = nid

    # 4-connected unit-weight edges (right and down only: no duplicates)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#":
                continue
            if c + 1 < len(row) and row[c + 1] != "#":
                g.add_edge(f"{r},{c}", f"{r},{c + 1}", 1.0)
            if r + 1 < len(rows) and rows[r + 1][c] != "#":
                g.add_edge(f"{r},{c}", f"{r + 1},{c}", 1.0)
    if not g.adjacency:
        raise GraphError("grid has no open cells")
    return g


def _parse_json(text: str) -> Graph:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise GraphError(f"invalid JSON: {exc}") from None
    if not isinstance(data, dict) or "nodes" not in data:
        raise GraphError('JSON graph needs at least {"nodes": [{"id": ...}]}')

    g = Graph(directed=bool(data.get("directed", False)))
    for node in data["nodes"]:
        try:
            nid = str(node["id"])
        except (KeyError, TypeError):
            raise GraphError("every node needs an \"id\"") from None
        g.add_node(nid, (node.get("x", 0.0), node.get("y", 0.0)))

    seen: set = set()
    for edge in data.get("edges", []):
        try:
            u, v = str(edge["from"]), str(edge["to"])
        except (KeyError, TypeError):
            raise GraphError('every edge needs "from" and "to"') from None
        # endpoints must be declared in "nodes" (catches typos loudly)
        missing = [x for x in (u, v) if x not in g.adjacency]
        if missing:
            raise GraphError(
                f"edge {u} -> {v} references undeclared node(s): {missing}")
        w = float(edge.get("w", 1.0))
        if not math.isfinite(w):
            raise GraphError(f"edge weight must be finite: {u} -> {v}")
        if not g.directed:
            key = tuple(sorted((u, v)))
            if key in seen or u == v:
                continue
            seen.add(key)
        elif u == v:
            raise GraphError(f"self-loop not allowed: {u}")
        g.adjacency[u].append((v, w))
        if not g.directed:
            g.adjacency[v].append((u, w))

    g.start = data.get("start")
    g.goal = data.get("goal")
    if g.start is not None and not g.has_node(str(g.start)):
        raise GraphError(f"start {g.start!r} not in graph")
    if g.goal is not None and not g.has_node(str(g.goal)):
        raise GraphError(f"goal {g.goal!r} not in graph")
    g.meta = dict(data.get("meta") or {})
    if not g.adjacency:
        raise GraphError("JSON graph has no nodes")
    return g


def parse_graph(text: str, fmt: str = "auto", directed: bool = False) -> Graph:
    """Parse graph text. ``fmt`` is auto|edge|grid|json."""
    if fmt not in ("auto", "edge", "grid", "json"):
        raise GraphError(f"unknown format: {fmt}")
    if fmt == "auto":
        if text.lstrip().startswith("{"):
            fmt = "json"
        elif _looks_like_grid([ln for ln in text.splitlines() if ln.strip()]):
            fmt = "grid"
        else:
            fmt = "edge"
    if fmt == "json":
        return _parse_json(text)
    if fmt == "grid":
        return _parse_grid(text)
    return _parse_edge_list(text, directed)


def load_graph(path: str, fmt: str = "auto", directed: bool = False) -> Graph:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise GraphError(f"cannot read {path}: {exc}") from None
    return parse_graph(text, fmt=fmt, directed=directed)


# -- generators -------------------------------------------------------------


def generate_grid(rows: int = 12, cols: int = 16, density: float = 0.25,
                  seed: int = 7) -> Graph:
    """Seeded random grid; S and T are guaranteed to be connected."""
    if rows < 2 or cols < 2:
        raise GraphError("grid needs at least 2x2 cells")
    if not 0.0 <= density < 1.0:
        raise GraphError("density must be in [0, 1)")
    rng = random.Random(seed)
    endpoints = {(0, 0), (rows - 1, cols - 1)}
    walls: set[tuple[int, int]] = set()
    for r in range(rows):
        for c in range(cols):
            if (r, c) in endpoints:
                continue
            if rng.random() < density:
                walls.add((r, c))

    def flood() -> set[tuple[int, int]]:
        seen = {(0, 0)}
        stack = [(0, 0)]
        while stack:
            r, c = stack.pop()
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if (0 <= nr < rows and 0 <= nc < cols
                        and (nr, nc) not in walls and (nr, nc) not in seen):
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return seen

    reachable = flood()
    goal = (rows - 1, cols - 1)
    guard = rows * cols
    while goal not in reachable and guard > 0:
        guard -= 1
        border = [w for w in walls
                  if any((w[0] + dr, w[1] + dc) in reachable
                         for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))]
        if not border:
            walls.clear()
            break
        walls.remove(rng.choice(sorted(border)))
        reachable = flood()

    g = Graph(directed=False,
              meta={"kind": "grid", "rows": rows, "cols": cols, "seed": seed})
    for r in range(rows):
        for c in range(cols):
            if (r, c) not in walls:
                g.add_node(f"{r},{c}", pos=(float(c), float(r)))
    for r in range(rows):
        for c in range(cols):
            if (r, c) in walls:
                continue
            if c + 1 < cols and (r, c + 1) not in walls:
                g.add_edge(f"{r},{c}", f"{r},{c + 1}", 1.0)
            if r + 1 < rows and (r + 1, c) not in walls:
                g.add_edge(f"{r},{c}", f"{r + 1},{c}", 1.0)
    g.start, g.goal = "0,0", f"{rows - 1},{cols - 1}"
    return g


def generate_graph(nodes: int = 10, edges: int | None = None,
                   directed: bool = False, weight_max: int = 10,
                   seed: int = 7, prefix: str = "N") -> Graph:
    """Seeded random graph; undirected graphs are guaranteed connected."""
    if nodes < 2:
        raise GraphError("need at least 2 nodes")
    if weight_max < 1:
        raise GraphError("weight-max must be >= 1")
    cap = nodes * (nodes - 1) if directed else nodes * (nodes - 1) // 2
    m = edges if edges is not None else min(cap, max(nodes, int(nodes * 1.6)))
    if m > cap:
        raise GraphError(f"edge count {m} exceeds possible unique edges {cap}")
    rng = random.Random(seed)
    ids = [f"{prefix}{i}" for i in range(nodes)]

    g = Graph(directed=directed, meta={"kind": "graph", "seed": seed})
    for nid in ids:
        g.add_node(nid, (round(rng.random(), 3), round(rng.random(), 3)))

    order = ids[:]
    rng.shuffle(order)
    pairs: set[tuple] = set()

    def try_add(a: str, b: str) -> bool:
        if a == b:
            return False
        key = (a, b) if directed else tuple(sorted((a, b)))
        if key in pairs:
            return False
        pairs.add(key)
        g.add_edge(a, b, float(rng.randint(1, weight_max)))
        return True

    # spanning chain first: undirected graphs end up connected,
    # and the chain itself gives every graph a reachable S/T pair
    for a, b in zip(order, order[1:]):
        try_add(a, b)
    guard = m * 50 + 100
    while len(pairs) < m and guard > 0:
        guard -= 1
        try_add(rng.choice(ids), rng.choice(ids))
    g.meta["edges"] = len(pairs)
    g.start, g.goal = (order[0], order[-1]) if order else (None, None)
    return g


def save_graph(g: Graph, path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(g.to_json() + "\n")