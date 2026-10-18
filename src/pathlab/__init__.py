"""pathlab — graph path-algorithm learning lab.

Trace Dijkstra, A*, Bellman-Ford and Floyd-Warshall step by step, render a
self-contained HTML visualizer, and drill with a seeded prediction quiz.
Standard library only; fully offline.
"""

__version__ = "1.0.0"

from .graph import Graph, load_graph, generate_grid, generate_graph
from .algorithms import Step, TraceResult, run_algorithm

__all__ = [
    "Graph",
    "load_graph",
    "generate_grid",
    "generate_graph",
    "Step",
    "TraceResult",
    "run_algorithm",
    "__version__",
]