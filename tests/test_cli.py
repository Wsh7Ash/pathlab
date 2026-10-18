import json
import os
import subprocess
import sys
import tempfile
import unittest

from tests import *  # noqa: F401,F403

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
EXAMPLES = os.path.join(ROOT, "examples")
TINY = os.path.join(EXAMPLES, "tiny.txt")
GRID = os.path.join(EXAMPLES, "grid_small.txt")
NEG = os.path.join(EXAMPLES, "negative.txt")
NEG_CYCLE = os.path.join(EXAMPLES, "negative_cycle.txt")

ENV = dict(os.environ, PYTHONPATH=SRC)


def run(*args, stdin_text=None):
    return subprocess.run(
        [sys.executable, "-m", "pathlab", *args],
        input=stdin_text, capture_output=True, text=True, encoding="utf-8",
        env=ENV, cwd=ROOT, timeout=60)


class GenTests(unittest.TestCase):
    def test_gen_grid_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "g.json")
            r = run("gen", "grid", "--rows", "6", "--cols", "7",
                    "--density", "0.2", "--seed", "4", "-o", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("wrote", r.stdout)
            with open(out, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["meta"]["rows"], 6)
            self.assertEqual(data["start"], "0,0")

    def test_gen_grid_to_stdout_is_json(self):
        r = run("gen", "grid", "--rows", "4", "--cols", "4", "--seed", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        json.loads(r.stdout)   # UTF-8 JSON survives the pipe

    def test_gen_graph_defaults(self):
        r = run("gen", "graph", "--nodes", "5", "--seed", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(len(data["nodes"]), 5)
        self.assertTrue(data["start"])

    def test_gen_validation_maps_to_exit_2(self):
        r = run("gen", "grid", "--rows", "1", "--cols", "4")
        self.assertEqual(r.returncode, 2)
        self.assertIn("pathlab:", r.stderr)


class TraceTests(unittest.TestCase):
    def test_text_trace(self):
        r = run("trace", TINY, "--algo", "dijkstra", "--start", "S",
                "--goal", "D")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("=== pathlab trace (dijkstra) ===", r.stdout)
        self.assertIn("cost 15", r.stdout)

    def test_json_trace(self):
        r = run("trace", TINY, "--algo", "dijkstra", "--start", "S",
                "--goal", "D", "--format", "json")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["path_cost"], 15)
        self.assertEqual(data["path"], ["S", "B", "D"])

    def test_grid_example(self):
        r = run("trace", GRID, "--algo", "astar", "--max-steps", "5")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("astar", r.stdout)
        self.assertIn("more steps", r.stdout)

    def test_negative_edge_example(self):
        r = run("trace", NEG, "--directed", "--algo", "bellman-ford",
                "--start", "S", "--goal", "C", "--format", "json")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["distances"]["A"], -1)
        self.assertIsNone(data["negative_cycle"])
        self.assertTrue(data["found"])
        self.assertEqual(data["path"][0], "S")

    def test_negative_cycle_example_exits_zero_but_reports(self):
        r = run("trace", NEG_CYCLE, "--directed", "--algo", "bellman-ford",
                "--start", "S", "--goal", "C")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NEGATIVE CYCLE", r.stdout)

    def test_missing_start_is_usage_error(self):
        r = run("trace", TINY, "--algo", "dijkstra")   # edgelist has no S
        self.assertEqual(r.returncode, 2)
        self.assertIn("start node is required", r.stderr)

    def test_missing_file_is_usage_error(self):
        r = run("trace", "/no/such/file.txt", "--start", "A")
        self.assertEqual(r.returncode, 2)
        self.assertIn("cannot read", r.stderr)

    def test_start_equals_goal_warns(self):
        r = run("trace", TINY, "--start", "S", "--goal", "S")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("same node", r.stderr)


class VizCliTests(unittest.TestCase):
    def test_viz_writes_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "v.html")
            r = run("viz", GRID, "--algo", "astar", "-o", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("wrote", r.stdout)
            with open(out, encoding="utf-8") as fh:
                body = fh.read()
            self.assertIn("<svg", body)
            self.assertIn("const P =", body)
            self.assertEqual(body.count("</script>"), 1)


class QuizCliTests(unittest.TestCase):
    def _answers(self, count, pick=1):
        return "".join(f"{pick}\n" for _ in range(count))

    def test_all_correct_answers_pass(self):
        from pathlab.graph import load_graph
        from pathlab.quiz import build_questions
        g = load_graph(os.path.join(EXAMPLES, "tiny.txt"), fmt="edge",
                       directed=True)
        qs = build_questions(g, "dijkstra", start="S", goal="D",
                             count=4, seed=11, options=4)
        # feed the 1-based index of the correct option for each question
        stdin_text = "".join(f"{q.answer_index + 1}\n" for q in qs)
        r = run("quiz", TINY, "--algo", "dijkstra", "--start", "S",
                "--goal", "D", "--questions", "4", "--seed", "11",
                stdin_text=stdin_text)
        self.assertEqual(r.returncode, 0,
                         f"stdout={r.stdout} stderr={r.stderr}")
        self.assertIn("100%", r.stdout)
        self.assertIn("PASS", r.stdout)

    def test_wrong_answers_fail_with_exit_1(self):
        r = run("quiz", GRID, "--algo", "dijkstra", "--questions", "3",
                "--seed", "7", stdin_text=self._answers(3, pick=9))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("0/3", r.stdout)
        self.assertIn("FAIL", r.stdout)

    def test_invalid_input_counts_as_wrong(self):
        r = run("quiz", GRID, "--algo", "dijkstra", "--questions", "3",
                "--seed", "2", stdin_text="")
        # EOF everywhere: still grades and fails (exit 1), never crashes
        self.assertEqual(r.returncode, 1, r.stderr)

    def test_options_render_numbered(self):
        r = run("quiz", GRID, "--algo", "dijkstra", "--questions", "1",
                "--seed", "3", stdin_text="1\n")
        # answered one question: grade is reported either way (0 or 1 exit)
        self.assertIn(r.returncode, (0, 1), r.stdout)
        self.assertIn("1)", r.stdout)
        self.assertIn("2)", r.stdout)
        self.assertIn("Q1.", r.stdout)


class VersionAndHelpTests(unittest.TestCase):
    def test_version(self):
        r = run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("pathlab 1.0.0", r.stdout)

    def test_help_lists_subcommands(self):
        r = run("--help")
        self.assertEqual(r.returncode, 0)
        for word in ("gen", "trace", "viz", "quiz"):
            self.assertIn(word, r.stdout)

    def test_unknown_command_exits_2(self):
        r = run("frobnicate")
        self.assertNotEqual(r.returncode, 0)

    def test_bad_algo_choice_exits_2(self):
        r = run("trace", TINY, "--algo", "kruskal")
        self.assertEqual(r.returncode, 2)

    def test_module_help_works(self):
        r = run("trace", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--algo", r.stdout)


if __name__ == "__main__":
    unittest.main()