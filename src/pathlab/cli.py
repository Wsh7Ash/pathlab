"""pathlab CLI: gen | trace | viz | quiz

Exit codes: 0 success (quiz at/above threshold), 1 quiz below threshold,
2 usage/input error.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .algorithms import ALGORITHMS, run_algorithm
from .explain import render_json, render_text
from .graph import (Graph, GraphError, generate_graph, generate_grid,
                    load_graph, save_graph)
from .quiz import build_questions, grade, parse_answer
from .viz import write_html


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pathlab",
        description="Trace, visualize and quiz graph path algorithms — offline.")
    p.add_argument("--version", action="version", version=f"pathlab {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("file", help="graph file (edge list, grid or JSON)")
        sp.add_argument("--algo", choices=ALGORITHMS, default="dijkstra")
        sp.add_argument("--start", help="start node (default: S in the file)")
        sp.add_argument("--goal", help="goal node (default: T in the file)")
        sp.add_argument("--input-format", choices=("auto", "edge", "grid", "json"),
                        default="auto", dest="input_format")
        sp.add_argument("--directed", action="store_true",
                        help="treat an edge list as directed")
        sp.add_argument("--heuristic", choices=("manhattan", "euclidean", "zero"),
                        default="manhattan", help="A* heuristic (default: manhattan)")

    gen = sub.add_parser("gen", help="generate a random graph or grid")
    gsub = gen.add_subparsers(dest="kind", required=True)

    gg = gsub.add_parser("grid", help="random grid with connected S/T")
    gg.add_argument("--rows", type=int, default=12)
    gg.add_argument("--cols", type=int, default=16)
    gg.add_argument("--density", type=float, default=0.25,
                    help="wall probability 0..1 (default 0.25)")
    gg.add_argument("--seed", type=int, default=7)
    gg.add_argument("--output", "-o", help="write here instead of stdout")

    gn = gsub.add_parser("graph", help="random weighted graph")
    gn.add_argument("--nodes", type=int, default=10)
    gn.add_argument("--edges", type=int, help="unique edge count (default: ~1.6n)")
    gn.add_argument("--directed", action="store_true")
    gn.add_argument("--weight-max", type=int, default=10)
    gn.add_argument("--seed", type=int, default=7)
    gn.add_argument("--output", "-o", help="write here instead of stdout")

    tr = sub.add_parser("trace", help="run an algorithm and print the step log")
    common(tr)
    tr.add_argument("--format", choices=("text", "json"), default="text")
    tr.add_argument("--max-steps", type=int, help="truncate the text log")

    vz = sub.add_parser("viz", help="write a self-contained HTML visualizer")
    common(vz)
    vz.add_argument("--output", "-o", default="pathlab.html")

    qz = sub.add_parser("quiz", help="step-prediction quiz (reads answers from stdin)")
    common(qz)
    qz.add_argument("--questions", type=int, default=5)
    qz.add_argument("--seed", type=int, default=11)
    qz.add_argument("--options", type=int, default=4, help="choices per question")
    qz.add_argument("--pass", type=float, default=70.0, dest="pass_pct",
                    help="pass threshold in percent (default 70)")
    return p


def _load(args) -> Graph:
    return load_graph(args.file, fmt=args.input_format, directed=args.directed)


def _resolve(graph: Graph, args) -> tuple[str | None, str | None]:
    start = args.start if args.start is not None else graph.start
    goal = args.goal if args.goal is not None else graph.goal
    return start, goal


def _cmd_gen(args) -> int:
    if args.kind == "grid":
        g = generate_grid(rows=args.rows, cols=args.cols,
                          density=args.density, seed=args.seed)
    else:
        g = generate_graph(nodes=args.nodes, edges=args.edges,
                           directed=args.directed, weight_max=args.weight_max,
                           seed=args.seed)
    text = g.to_json()
    if args.output:
        save_graph(g, args.output)
        print(f"wrote {args.output}: {len(g.nodes)} nodes, "
              f"{len(g.edges())} edges (S={g.start}, T={g.goal})")
    else:
        print(text)
    return 0


def _cmd_trace(args) -> int:
    graph = _load(args)
    start, goal = _resolve(graph, args)
    result = run_algorithm(graph, args.algo, start=start, goal=goal,
                           heuristic=args.heuristic)
    if start == goal and start is not None:
        print("note: start and goal are the same node", file=sys.stderr)
    if args.format == "json":
        print(render_json(result))
    else:
        print(render_text(result, max_steps=args.max_steps))
    return 0


def _cmd_viz(args) -> int:
    graph = _load(args)
    start, goal = _resolve(graph, args)
    result = run_algorithm(graph, args.algo, start=start, goal=goal,
                           heuristic=args.heuristic)
    size = write_html(graph, result, args.output,
                      title=f"pathlab — {args.algo} on {args.file}")
    print(f"wrote {args.output} ({size} bytes, {len(result.steps)} steps)")
    print(result.summary())
    return 0


def _cmd_quiz(args) -> int:
    graph = _load(args)
    start, goal = _resolve(graph, args)
    questions = build_questions(graph, args.algo, start=start, goal=goal,
                                count=args.questions, seed=args.seed,
                                options=args.options)
    print(f"pathlab quiz — {args.algo} on {args.file} "
          f"({len(questions)} questions, pass mark {args.pass_pct:g}%)\n")
    picks: list[str | None] = []
    for q in questions:
        print(q.format())
        try:
            if sys.stdin.isatty():
                print()
                line = input(f"your answer (1-{len(q.options)}): ")
            else:
                print("  (stdin: enter option number)")
                line = input("> ")
        except (EOFError, KeyboardInterrupt):
            line = ""
        picks.append(parse_answer(line, q.options))
        print()
    result = grade(questions, picks, pass_pct=args.pass_pct)
    print(result.report())
    return 0 if result.passed else 1


def _force_utf8_stdio() -> None:
    """Windows pipes default to the locale codepage and choke on ∞/· output."""
    for stream in (sys.stdout, sys.stderr):
        reconf = getattr(stream, "reconfigure", None)
        if reconf is None:
            continue
        try:
            reconf(encoding="utf-8", errors="replace")
        except (OSError, ValueError):   # pragma: no cover
            pass


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        _force_utf8_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "gen":
            return _cmd_gen(args)
        if args.command == "trace":
            return _cmd_trace(args)
        if args.command == "viz":
            return _cmd_viz(args)
        return _cmd_quiz(args)
    except (GraphError, ValueError, OSError) as exc:
        print(f"pathlab: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(main())