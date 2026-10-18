import os
import tempfile
import unittest

from tests import *  # noqa: F401,F403

from pathlab.algorithms import bellman_ford, dijkstra, floyd_warshall
from pathlab.graph import parse_graph
from pathlab.viz import build_html, write_html

TINY = "S A 7\nS B 9\nA C 15\nB C 11\nB D 6\nC D 9\nA B 10\n"
NEG_CYCLE = "S A 2\nA B -1\nB A -1\nB C 1\n"


class VizTests(unittest.TestCase):
    def setUp(self):
        self.graph = parse_graph(TINY, directed=True)
        self.result = dijkstra(self.graph, "S", "D")
        self.html = build_html(self.graph, self.result)

    def test_self_contained_no_external_resources(self):
        self.assertIn("<svg", self.html)
        self.assertNotIn("<script src", self.html)
        self.assertNotIn("<link ", self.html)
        self.assertNotIn("@import", self.html)
        # only our own opening/closing script tags exist
        self.assertEqual(self.html.count("<script>"), 1)
        self.assertEqual(self.html.count("</script>"), 1)

    def test_payload_contains_graph_and_steps(self):
        marker = "const P = {"
        start = self.html.index(marker)
        end = self.html.index("};", start)
        import json
        payload = json.loads(self.html[start + len("const P = "):end + 1]
                             .rsplit("}", 1)[0] + "}")
        self.assertEqual(len(payload["steps"]), len(self.result.steps))
        self.assertEqual(payload["path"], ["S", "B", "D"])
        node_ids = {n["id"] for n in payload["graph"]["nodes"]}
        self.assertEqual(node_ids, set(self.graph.nodes))

    def test_script_breakout_is_escaped(self):
        g = parse_graph('{"nodes": [{"id": "</script><b>"}], "edges": []}',
                        fmt="json")
        r = floyd_warshall(g, start="</script><b>")
        out = build_html(g, r)
        # data cannot close the script element early: only our own tags remain
        self.assertEqual(out.count("</script>"), 1)
        self.assertIn("<\\/", out)

    def test_summary_is_escaped_in_title_area(self):
        g = parse_graph('{"nodes": [{"id": "a<b"}], "edges": []}', fmt="json")
        r = floyd_warshall(g)
        out = build_html(g, r, title="x<y & z")
        self.assertIn("x&lt;y &amp; z", out)

    def test_element_ids_exist(self):
        for element_id in ('id="svg"', 'id="scrub"', 'id="action"',
                           'id="pathlayer"', 'id="first"', 'id="last"'):
            self.assertIn(element_id, self.html)

    def test_negative_cycle_markup(self):
        g = parse_graph(NEG_CYCLE, directed=True)
        r = bellman_ford(g, "S", "C")
        out = build_html(g, r)
        self.assertIn('"cycle":', out)
        self.assertIn("neg-cycle", out)

    def test_write_html_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.html")
            size = write_html(self.graph, self.result, path)
            self.assertGreater(size, 1000)
            actual = os.path.getsize(path)
            self.assertEqual(actual, size)
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
            self.assertTrue(body.startswith("<!doctype html>"))
            self.assertTrue(body.rstrip().endswith("</html>"))


if __name__ == "__main__":
    unittest.main()