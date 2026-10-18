import json
import os
import tempfile
import unittest

from tests import *  # noqa: F401,F403  (puts src/ on sys.path)

from pathlab.graph import (Graph, GraphError, generate_graph, generate_grid,
                           load_graph, parse_graph, save_graph)


class EdgeListTests(unittest.TestCase):
    def test_basic_edges_and_default_weight(self):
        g = parse_graph("A B\nB C 2.5\n")
        self.assertEqual(g.nodes, ["A", "B", "C"])
        self.assertEqual(g.weight("A", "B"), 1.0)
        self.assertEqual(g.weight("B", "C"), 2.5)

    def test_undirected_edges_go_both_ways(self):
        g = parse_graph("A B 3\n")
        self.assertEqual(g.neighbors("A"), [("B", 3.0)])
        self.assertEqual(g.neighbors("B"), [("A", 3.0)])

    def test_directed_flag_adds_one_way(self):
        g = parse_graph("A B 3\n", directed=True)
        self.assertEqual(g.neighbors("A"), [("B", 3.0)])
        self.assertEqual(g.neighbors("B"), [])

    def test_comments_and_blank_lines(self):
        g = parse_graph("# header\n\nA B 2  # trailing\n\n# end\n")
        self.assertEqual(g.nodes, ["A", "B"])
        self.assertEqual(len(g.edges()), 1)

    def test_errors(self):
        with self.assertRaises(GraphError):
            parse_graph("")                       # no edges
        with self.assertRaises(GraphError):
            parse_graph("A B nope\n")             # bad weight
        with self.assertRaises(GraphError):
            parse_graph("A A 1\n")                # self-loop
        with self.assertRaises(GraphError):
            parse_graph("A B 1 extra 4\n")        # too many tokens
        with self.assertRaises(GraphError):
            parse_graph("A B\n", fmt="wat")       # unknown format

    def test_negative_weights_allowed(self):
        g = parse_graph("A B -2\n")
        self.assertEqual(g.weight("A", "B"), -2.0)

    def test_edges_are_deduplicated_for_drawing(self):
        g = parse_graph("A B 1\nA B 1\nB A 1\n")
        self.assertEqual(len(g.edges()), 1)

    def test_to_dict_round_trip(self):
        g = parse_graph("A B 4\nB C 2\n")
        g2 = parse_graph(g.to_json(), fmt="json")
        self.assertEqual(g2.nodes, g.nodes)
        self.assertEqual(g2.weight("A", "B"), 4.0)
        self.assertEqual(g2.weight("B", "C"), 2.0)


class GridTests(unittest.TestCase):
    GRID = "S..#\n.#....\n"  # noqa: E501  (intentional ragged test lives below)

    def test_parse_grid_counts_and_markers(self):
        g = parse_graph("S.#\n..#\n#T.\n")
        self.assertEqual(sorted(g.nodes),
                         ["0,0", "0,1", "1,0", "1,1", "2,1", "2,2"])
        self.assertEqual(g.start, "0,0")
        self.assertEqual(g.goal, "2,1")
        self.assertEqual(g.meta["rows"], 3)
        self.assertEqual(g.meta["cols"], 3)

    def test_grid_is_4_connected(self):
        g = parse_graph("ST\n..\n")
        # S-T adjacent horizontally, S-down exists, no diagonals
        self.assertEqual(sorted(n for n, _ in g.neighbors("0,0")),
                         ["0,1", "1,0"])

    def test_ragged_grid_rejected(self):
        with self.assertRaises(GraphError):
            parse_graph("ST\n....\n")

    def test_bad_chars_rejected(self):
        with self.assertRaises(GraphError):
            parse_graph("SX\n..\n", fmt="grid")

    def test_autodetect_prefers_grid_only_with_markers(self):
        grid = parse_graph("S.T\n...")
        self.assertEqual(grid.meta["kind"], "grid")
        not_grid = parse_graph("A B\nB C\n")   # plain words, no S/T marker
        self.assertIsNone(not_grid.meta.get("kind"))

    def test_json_autodetect(self):
        g = parse_graph('{"nodes": [{"id": "A"}], "edges": []}')
        self.assertEqual(g.nodes, ["A"])


class JsonTests(unittest.TestCase):
    def test_positions_and_markers(self):
        g = parse_graph(json.dumps({
            "nodes": [{"id": "A", "x": 1, "y": 2}, {"id": "B"}],
            "edges": [{"from": "A", "to": "B", "w": 3}],
            "start": "A", "goal": "B",
        }), fmt="json")
        self.assertEqual(g.positions["A"], (1.0, 2.0))
        self.assertEqual((g.start, g.goal), ("A", "B"))
        self.assertEqual(g.weight("A", "B"), 3.0)

    def test_undirected_duplicates_collapsed(self):
        g = parse_graph(json.dumps({
            "nodes": [{"id": "A"}, {"id": "B"}],
            "edges": [{"from": "A", "to": "B", "w": 1},
                      {"from": "B", "to": "A", "w": 9}],
        }), fmt="json")
        self.assertEqual(len(g.adjacency["A"]), 1)
        self.assertEqual(len(g.adjacency["B"]), 1)
        self.assertEqual(g.weight("A", "B"), 1.0)

    def test_json_errors(self):
        with self.assertRaises(GraphError):
            parse_graph("{oops", fmt="json")
        with self.assertRaises(GraphError):
            parse_graph('{"nodes": [{"nope": 1}]}', fmt="json")
        with self.assertRaises(GraphError):
            parse_graph(json.dumps({"nodes": [{"id": "A"}],
                                    "edges": [{"from": "A", "to": "Z"}]}),
                        fmt="json")   # unknown endpoint
        with self.assertRaises(GraphError):
            parse_graph(json.dumps({"nodes": [{"id": "A"}],
                                    "start": "Q"}), fmt="json")


class GeneratorTests(unittest.TestCase):
    def test_grid_is_deterministic_and_connected(self):
        a = generate_grid(rows=10, cols=12, density=0.3, seed=4)
        b = generate_grid(rows=10, cols=12, density=0.3, seed=4)
        self.assertEqual(a.to_json(), b.to_json())
        c = generate_grid(rows=10, cols=12, density=0.3, seed=5)
        self.assertNotEqual(a.to_json(), c.to_json())
        # S can reach T
        seen = {a.start}
        stack = [a.start]
        while stack:
            cur = stack.pop()
            for nb, _w in a.neighbors(cur):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        self.assertIn(a.goal, seen)

    def test_grid_validates_inputs(self):
        with self.assertRaises(GraphError):
            generate_grid(rows=1, cols=5)
        with self.assertRaises(GraphError):
            generate_grid(rows=5, cols=5, density=1.0)
        with self.assertRaises(GraphError):
            generate_grid(rows=5, cols=5, density=-0.1)

    def test_graph_generator_counts_and_range(self):
        g = generate_graph(nodes=8, edges=11, seed=2, weight_max=6)
        self.assertEqual(len(g.nodes), 8)
        self.assertEqual(len(g.edges()), 11)
        self.assertEqual(len(g.arcs()), 22)       # undirected -> double arcs
        for _u, _v, w in g.edges():
            self.assertTrue(1 <= w <= 6)
        g2 = generate_graph(nodes=8, edges=11, seed=2, weight_max=6)
        self.assertEqual(g.to_json(), g2.to_json())

    def test_graph_generator_marks_start_and_goal(self):
        g = generate_graph(nodes=6, seed=9)
        self.assertIn(g.start, g.adjacency)
        self.assertIn(g.goal, g.adjacency)
        self.assertNotEqual(g.start, g.goal)

    def test_graph_generator_connectivity(self):
        g = generate_graph(nodes=15, edges=22, seed=3)
        seen = {g.start}
        stack = [g.start]
        while stack:
            cur = stack.pop()
            for nb, _w in g.neighbors(cur):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        self.assertEqual(seen, set(g.nodes))

    def test_graph_generator_validates(self):
        with self.assertRaises(GraphError):
            generate_graph(nodes=1)
        with self.assertRaises(GraphError):
            generate_graph(nodes=4, edges=99)
        with self.assertRaises(GraphError):
            generate_graph(nodes=4, weight_max=0)

    def test_save_and_load_round_trip(self):
        g = generate_grid(rows=6, cols=6, density=0.2, seed=1)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "g.json")
            save_graph(g, path)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)          # file is valid JSON
            g2 = load_graph(path, fmt="json")
            self.assertEqual(g2.to_json(), g.to_json())
        with self.assertRaises(GraphError):
            load_graph("/nonexistent/nowhere.txt")

    def test_graph_object_helpers(self):
        g = Graph(directed=True)
        g.add_edge("A", "B", 2)
        self.assertEqual(g.arcs(), [("A", "B", 2.0)])
        self.assertEqual(g.edges(), [("A", "B", 2.0)])
        with self.assertRaises(GraphError):
            g.weight("B", "A")
        with self.assertRaises(GraphError):
            g.add_node("X")
            g.add_edge("X", "X")


if __name__ == "__main__":
    unittest.main()