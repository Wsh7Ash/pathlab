import json
import unittest

from tests import *  # noqa: F401,F403

from pathlab.algorithms import dijkstra
from pathlab.explain import render_json, render_text, render_verdict
from pathlab.graph import parse_graph

TINY = "S A 7\nS B 9\nA C 15\nB C 11\nB D 6\nC D 9\nA B 10\n"


class ExplainTests(unittest.TestCase):
    def setUp(self):
        self.result = dijkstra(parse_graph(TINY, directed=True), "S", "D")

    def test_render_text_has_header_and_steps(self):
        out = render_text(self.result)
        self.assertIn("=== pathlab trace (dijkstra) ===", out)
        self.assertIn("[init", out)
        self.assertIn("[settle", out)
        self.assertIn("note:", out)

    def test_render_text_truncates(self):
        full = render_text(self.result)
        cut = render_text(self.result, max_steps=3)
        self.assertIn("more steps", cut)
        self.assertLess(len(cut), len(full))
        # header survives truncation
        self.assertIn("=== pathlab trace", cut)
        # exact count of hidden steps is reported
        hidden = len(self.result.steps) - 3
        self.assertIn(f"... {hidden} more steps", cut)

    def test_render_json_round_trips(self):
        data = json.loads(render_json(self.result))
        self.assertEqual(data["algo"], "dijkstra")
        self.assertEqual(len(data["steps"]), len(self.result.steps))
        self.assertEqual(data["path"], ["S", "B", "D"])
        self.assertEqual(data["path_cost"], 15)
        self.assertTrue(data["found"])
        # every step carries its own snapshot
        first = data["steps"][0]
        for key in ("seq", "action", "text", "dist", "settled", "frontier"):
            self.assertIn(key, first)

    def test_render_json_inf_becomes_null(self):
        g = parse_graph("A B 1\nX Y 1\n")
        r = dijkstra(g, "A", "Y")
        raw = render_json(r)
        # no bare Infinity token (invalid JSON)
        self.assertNotIn("Infinity", raw)
        data = json.loads(raw)
        self.assertFalse(data["found"])

    def test_verdict_is_summary(self):
        self.assertEqual(render_verdict(self.result), self.result.summary())


if __name__ == "__main__":
    unittest.main()