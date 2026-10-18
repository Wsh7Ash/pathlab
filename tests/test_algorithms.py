import math
import unittest

from tests import *  # noqa: F401,F403

from pathlab.algorithms import (ALGORITHMS, astar, bellman_ford, dijkstra,
                                floyd_warshall, run_algorithm)
from pathlab.graph import generate_graph, parse_graph

TINY = """
S A 7
S B 9
A B 10
A C 15
B C 11
B D 6
C D 9
"""

GRID = "S...#....\n.#...#..#\n..##...#.\n.#..##..#\n#...#..#.\n.........\n...##..#T\n"

NEG = "S A 5\nS B 2\nB A -3\nA C 1\n"
NEG_CYCLE = "S A 2\nA B -1\nB A -1\nB C 1\n"


class DijkstraTests(unittest.TestCase):
    def test_textbook_distances_and_path(self):
        g = parse_graph(TINY, directed=True)
        r = dijkstra(g, "S", "D")
        self.assertTrue(r.found)
        self.assertEqual(r.distances,
                         {"S": 0, "A": 7, "B": 9, "D": 15, "C": 20})
        self.assertEqual(r.path, ["S", "B", "D"])
        self.assertEqual(r.path_cost, 15)
        # early stop at the goal: C was never settled
        self.assertEqual(r.settled, ["A", "B", "D", "S"])

    def test_step_stream_shape_and_text(self):
        r = dijkstra(parse_graph(TINY, directed=True), "S", "D")
        self.assertEqual(r.steps[0].action, "init")
        self.assertEqual(r.steps[1].action, "settle")
        self.assertEqual(r.steps[1].node, "S")
        self.assertEqual(r.steps[-1].action, "done")
        self.assertEqual([s.seq for s in r.steps],
                         list(range(len(r.steps))))
        self.assertIn("goal", [s.action for s in r.steps])
        texts = " ".join(s.text for s in r.steps)
        self.assertIn("settle S", texts)
        self.assertIn("relax", texts)

    def test_snapshots_are_consistent(self):
        g = parse_graph(TINY, directed=True)
        r = dijkstra(g, "S", "D")
        prev_settled: set[str] = set()
        for s in r.steps:
            self.assertFalse(set(s.settled) & set(s.frontier),
                             f"node both settled and in frontier at {s.seq}")
            self.assertLessEqual(prev_settled, set(s.settled),
                                 f"settled set shrank at {s.seq}")
            prev_settled = set(s.settled)
            self.assertTrue(set(s.dist) <= set(g.nodes),
                            f"dist snapshot has foreign keys at {s.seq}")
            # finite snapshot values are exactly the non-inf distances
            for key, val in s.dist.items():
                self.assertNotEqual(val, math.inf)

    def test_unreachable_goal(self):
        g = parse_graph("A B 1\nX Y 1\n")
        r = dijkstra(g, "A", "B")   # self reachable-ish: A-B fine...
        self.assertTrue(r.found)
        r2 = dijkstra(g, "A", "Y")
        self.assertFalse(r2.found)
        self.assertIsNone(r2.path)
        self.assertIn("no-path", [s.action for s in r2.steps])
        self.assertIn("unreachable", " ".join(s.text for s in r2.steps))

    def test_without_goal_runs_to_completion(self):
        r = dijkstra(parse_graph(TINY, directed=True), "S", None)
        self.assertIsNone(r.goal)
        self.assertFalse(r.found)
        self.assertEqual(len(r.settled), 5)
        self.assertNotIn("no-path", [s.action for s in r.steps])

    def test_input_validation(self):
        g = parse_graph(TINY, directed=True)
        with self.assertRaises(ValueError):
            dijkstra(g, "NOPE")
        with self.assertRaises(ValueError):
            dijkstra(g, None)
        with self.assertRaises(ValueError):
            dijkstra(g, "S", "NOPE")

    def test_golden_grid_path(self):
        g = parse_graph(GRID)
        r = dijkstra(g, "0,0", "6,8")
        self.assertTrue(r.found)
        self.assertEqual(r.path[0], "0,0")
        self.assertEqual(r.path[-1], "6,8")
        self.assertEqual(r.path_cost, 14)
        # every hop is a genuine 4-neighbour step
        for a, b in zip(r.path, r.path[1:]):
            ar, ac = (int(x) for x in a.split(","))
            br, bc = (int(x) for x in b.split(","))
            self.assertEqual(abs(ar - br) + abs(ac - bc), 1, f"{a} -> {b}")


class AStarTests(unittest.TestCase):
    def test_matches_dijkstra_on_unit_grid(self):
        g = parse_graph(GRID)
        d = dijkstra(g, "0,0", "6,8")
        a = astar(g, "0,0", "6,8", heuristic="manhattan")
        # both stop at the goal, so maps are partial: every distance A* did
        # compute must equal Dijkstra's, and A* knows a subset of the nodes
        self.assertLessEqual(set(a.distances), set(d.distances))
        for node, cost in a.distances.items():
            self.assertEqual(d.distances[node], cost, node)
        self.assertEqual(a.path_cost, d.path_cost)
        self.assertEqual(a.path[0], "0,0")
        self.assertEqual(a.path[-1], "6,8")
        self.assertIn("manhattan", a.note)
        # A* settles no more nodes than Dijkstra did
        self.assertLessEqual(len(a.settled), len(d.settled))

    def test_step_text_shows_g_h_f(self):
        r = astar(parse_graph(GRID), "0,0", "6,8")
        first_settle = next(s for s in r.steps if s.action == "settle")
        self.assertIn("g=", first_settle.text)
        self.assertIn("h=", first_settle.text)
        self.assertIn("f=", first_settle.text)

    def test_requires_goal(self):
        with self.assertRaises(ValueError):
            astar(parse_graph(GRID), "0,0", None)

    def test_zero_heuristic_equals_dijkstra(self):
        g = parse_graph(TINY, directed=True)   # no positions -> must use zero
        with self.assertRaises(ValueError):
            astar(g, "S", "D")
        a = astar(g, "S", "D", heuristic="zero")
        d = dijkstra(g, "S", "D")
        self.assertEqual(a.path_cost, d.path_cost)

    def test_unknown_heuristic_rejected(self):
        with self.assertRaises(ValueError):
            astar(parse_graph(GRID), "0,0", "6,8", heuristic="magic")


class BellmanFordTests(unittest.TestCase):
    def test_agrees_with_dijkstra_on_non_negative(self):
        g = parse_graph(TINY, directed=True)
        b = bellman_ford(g, "S", "D")
        d = dijkstra(g, "S", "D")
        self.assertEqual(b.distances, d.distances)
        self.assertTrue(b.found)
        self.assertIsNone(b.negative_cycle)
        self.assertIn("handles negative edge weights", b.note)

    def test_converged_after_last_round_is_not_a_cycle(self):
        # chain of 6 keeps improving right up to round n-1, then converges
        chain = "".join(f"N{i} N{i + 1} 1\n" for i in range(5))
        r = bellman_ford(parse_graph(chain, directed=True), "N0", "N5")
        self.assertIsNone(r.negative_cycle)
        self.assertTrue(r.found)
        self.assertEqual(r.path_cost, 5)
        detected = [s.action for s in r.steps]
        self.assertNotIn("neg-cycle", detected)

    def test_single_node_graph_has_no_cycle(self):
        g = parse_graph('{"nodes": [{"id": "A"}], "edges": []}', fmt="json")
        r = bellman_ford(g, "A")
        self.assertIsNone(r.negative_cycle)
        self.assertEqual(r.distances, {"A": 0})

    def test_negative_edge_without_cycle(self):
        g = parse_graph(NEG, directed=True)
        r = bellman_ford(g, "S", "C")
        self.assertIsNone(r.negative_cycle)
        self.assertEqual(r.distances, {"S": 0, "B": 2, "A": -1, "C": 0})
        self.assertTrue(r.found)
        self.assertEqual(r.path, ["S", "B", "A", "C"])

    def test_dijkstra_on_negative_edges_is_not_used_as_truth(self):
        # documented behavior: BF is the tool for negative weights
        g = parse_graph(NEG, directed=True)
        b = bellman_ford(g, "S", "C")
        self.assertEqual(b.distances["A"], -1)

    def test_reachable_negative_cycle_detected(self):
        g = parse_graph(NEG_CYCLE, directed=True)
        r = bellman_ford(g, "S", "C")
        self.assertIsNotNone(r.negative_cycle)
        self.assertTrue(set(r.negative_cycle) <= {"A", "B"})
        self.assertEqual(r.distances, {})
        self.assertFalse(r.found)
        self.assertIn("neg-cycle", [s.action for s in r.steps])
        self.assertIn("invalid", r.note)
        # cycle entries are contiguous under predecessor links
        self.assertEqual(len(r.negative_cycle), len(set(r.negative_cycle)))

    def test_cycle_string_is_closed(self):
        r = bellman_ford(parse_graph(NEG_CYCLE, directed=True), "S", "C")
        step = next(s for s in r.steps if s.action == "neg-cycle")
        self.assertIn("negative cycle:", step.text)


class FloydWarshallTests(unittest.TestCase):
    def test_agrees_with_dijkstra_for_every_pair(self):
        g = parse_graph(TINY, directed=True)
        fw = floyd_warshall(g)
        for s in g.nodes:
            d = dijkstra(g, s, None)
            for t in g.nodes:
                if t == s:
                    continue
                got = fw.distances.get(f"{s}->{t}")
                want = d.distances.get(t)
                if want is None:
                    self.assertIsNone(got, f"{s}->{t}")
                else:
                    self.assertEqual(got, want, f"{s}->{t}")

    def test_path_reconstruction(self):
        g = parse_graph(TINY, directed=True)
        r = floyd_warshall(g, start="S", goal="D")
        self.assertTrue(r.found)
        self.assertEqual(r.path[0], "S")
        self.assertEqual(r.path[-1], "D")
        self.assertEqual(r.path_cost, 15)

    def test_improve_steps_reference_existing_pairs(self):
        r = floyd_warshall(parse_graph(GRID))
        improves = [s for s in r.steps if s.action == "improve"]
        self.assertTrue(improves)
        for s in improves:
            self.assertIsNotNone(s.edge)
            self.assertNotEqual(s.edge[0], s.edge[1])
        self.assertEqual(r.steps[-1].action, "done")

    def test_negative_cycle_shows_on_diagonal(self):
        g = parse_graph(NEG_CYCLE, directed=True)
        r = floyd_warshall(g, start="S", goal="C")
        self.assertIsNotNone(r.negative_cycle)
        self.assertFalse(r.found)
        self.assertIn("neg-cycle", [s.action for s in r.steps])

    def test_step_log_is_capped(self):
        import json
        # complete DAG with w(i,j)=(j-i)^2 improves at many pivots per pair
        n = 20
        payload = {
            "directed": True,
            "nodes": [{"id": f"n{i}"} for i in range(n)],
            "edges": [{"from": f"n{i}", "to": f"n{j}", "w": (j - i) ** 2}
                       for i in range(n) for j in range(i + 1, n)],
        }
        g = parse_graph(json.dumps(payload), fmt="json")
        r = floyd_warshall(g)
        logged = [s for s in r.steps if s.action == "improve"]
        self.assertEqual(len(logged), 400)
        self.assertIn("not logged", r.steps[-1].text)

    def test_large_graph_gets_a_warning_in_the_first_step(self):
        n = 45
        from pathlab.graph import Graph
        g = Graph(directed=True)
        for i in range(n):
            for j in range(i + 1, n):
                g.add_edge(f"n{i}", f"n{j}", float((j - i) ** 2))
        r = floyd_warshall(g)
        self.assertIn("warning", r.steps[0].text)


class DispatchTests(unittest.TestCase):
    def test_every_algorithm_runs_through_dispatch(self):
        g = parse_graph(TINY, directed=True)
        for algo in ALGORITHMS:
            r = run_algorithm(g, algo, start="S", goal="D")
            self.assertEqual(r.algo, algo)
            self.assertGreater(len(r.steps), 2)

    def test_unknown_algorithm_rejected(self):
        with self.assertRaises(ValueError):
            run_algorithm(parse_graph(TINY, directed=True), "kruskal")

    def test_generated_graph_works_for_all(self):
        g = generate_graph(nodes=9, seed=6)
        for algo in ALGORITHMS:
            r = run_algorithm(g, algo, start=g.start, goal=g.goal)
            self.assertEqual(r.algo, algo)
            if algo in ("dijkstra", "astar", "bellman-ford"):
                self.assertTrue(r.found, f"{algo} should find the chain path")

    def test_summary_mentions_key_outcomes(self):
        r = dijkstra(parse_graph(TINY, directed=True), "S", "D")
        s = r.summary()
        self.assertIn("dijkstra S -> D", s)
        self.assertIn("cost 15", s)


if __name__ == "__main__":
    unittest.main()