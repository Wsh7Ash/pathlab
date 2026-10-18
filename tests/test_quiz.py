import unittest

from tests import *  # noqa: F401,F403

from pathlab.graph import parse_graph
from pathlab.quiz import (build_questions, grade, parse_answer)

TINY = "S A 7\nS B 9\nA C 15\nB C 11\nB D 6\nC D 9\nA B 10\n"
GRID = "S...#....\n.#...#..#\n..##...#.\n.#..##..#\n#...#..#.\n.........\n...##..#T\n"


class BuildQuestionsTests(unittest.TestCase):
    def test_question_shape(self):
        g = parse_graph(TINY, directed=True)
        qs = build_questions(g, "dijkstra", start="S", goal="D",
                             count=4, seed=5, options=4)
        self.assertEqual(len(qs), 4)
        for q in qs:
            self.assertEqual(len(q.options), 4)
            self.assertEqual(len(set(q.options)), 4, "options must be unique")
            self.assertIn(q.answer, q.options)
            self.assertIn("settles next", q.prompt)
            self.assertIn("settled:", q.context)
            self.assertIn("frontier:", q.context)
        self.assertEqual([q.index for q in qs], [0, 1, 2, 3])

    def test_questions_are_ordered_by_step(self):
        g = parse_graph(TINY, directed=True)
        qs = build_questions(g, "dijkstra", start="S", goal="D", count=3)
        seqs = [q.after_step for q in qs]
        self.assertEqual(seqs, sorted(seqs))
        self.assertEqual(len(set(seqs)), 3, "no duplicate decision points")

    def test_same_seed_is_reproducible(self):
        g = parse_graph(TINY, directed=True)
        a = build_questions(g, "dijkstra", start="S", goal="D", seed=3)
        b = build_questions(g, "dijkstra", start="S", goal="D", seed=3)
        self.assertEqual([q.options for q in a], [q.options for q in b])

    def test_seed_changes_option_layout(self):
        g = parse_graph(GRID)
        a = build_questions(g, "dijkstra", start="0,0", goal="6,8", count=8, seed=1)
        b = build_questions(g, "dijkstra", start="0,0", goal="6,8", count=8, seed=2)
        self.assertNotEqual([q.options for q in a], [q.options for q in b])

    def test_count_capped_by_available_decisions(self):
        g = parse_graph("A B 1\nB C 1\n")
        qs = build_questions(g, "dijkstra", start="A", goal="C", count=50)
        self.assertLessEqual(len(qs), 3)
        self.assertGreaterEqual(len(qs), 2)

    def test_too_small_graph_raises(self):
        g = parse_graph('{"nodes": [{"id": "A"}, {"id": "B"}], "edges": []}',
                        fmt="json")
        with self.assertRaises(ValueError):
            build_questions(g, "dijkstra", start="A", count=3)
        with self.assertRaises(ValueError):
            build_questions(parse_graph(TINY, directed=True), "dijkstra",
                            start="S", count=0)

    def test_bellman_ford_asks_about_edges(self):
        g = parse_graph("S A 5\nS B 2\nB A -3\nA C 1\n", directed=True)
        qs = build_questions(g, "bellman-ford", start="S", goal="C",
                             count=3, seed=1)
        self.assertTrue(qs)
        for q in qs:
            self.assertIn("relaxes next", q.prompt)
            self.assertIn("->", q.answer)

    def test_floyd_warshall_asks_about_pairs(self):
        g = parse_graph(TINY, directed=True)
        qs = build_questions(g, "floyd-warshall", start="S", goal="D",
                             count=3, seed=1)
        self.assertTrue(qs)
        for q in qs:
            self.assertIn("improves next", q.prompt)
            self.assertNotEqual(q.answer.split("->")[0], q.answer.split("->")[1])


class GradeTests(unittest.TestCase):
    def _fresh(self, seed=5):
        g = parse_graph(TINY, directed=True)
        return build_questions(g, "dijkstra", start="S", goal="D",
                               count=4, seed=seed)

    def test_all_correct(self):
        qs = self._fresh()
        picks = [q.answer for q in qs]
        r = grade(qs, picks, pass_pct=70)
        self.assertEqual(r.correct, 4)
        self.assertEqual(r.score_pct, 100)
        self.assertTrue(r.passed)
        self.assertIn("PASS", r.report())

    def test_all_wrong_fails(self):
        qs = self._fresh()
        picks = ["not-a-node"] * len(qs)
        r = grade(qs, picks, pass_pct=70)
        self.assertEqual(r.correct, 0)
        self.assertEqual(r.score_pct, 0)
        self.assertFalse(r.passed)
        self.assertIn("FAIL", r.report())
        self.assertIn("MISS", r.report())

    def test_none_answers_are_wrong(self):
        qs = self._fresh()
        picks = [None if i % 2 else q.answer for i, q in enumerate(qs)]
        r = grade(qs, picks)
        self.assertEqual(r.correct, 2)
        self.assertEqual(r.score_pct, 50)
        self.assertFalse(r.passed)

    def test_threshold_is_inclusive(self):
        qs = self._fresh()
        picks = [q.answer if i < 3 else "zzz" for i, q in enumerate(qs)]
        r = grade(qs, picks, pass_pct=75)
        self.assertEqual(r.score_pct, 75)
        self.assertTrue(r.passed)
        r2 = grade(qs, picks, pass_pct=76)
        self.assertFalse(r2.passed)

    def test_wrong_answer_count_rejected(self):
        qs = self._fresh()
        with self.assertRaises(ValueError):
            grade(qs, [])


class ParseAnswerTests(unittest.TestCase):
    OPTS = ["N1", "N2", "N3", "N4"]

    def test_numbers_are_one_based(self):
        self.assertEqual(parse_answer("1", self.OPTS), "N1")
        self.assertEqual(parse_answer(" 4 ", self.OPTS), "N4")
        self.assertIsNone(parse_answer("0", self.OPTS))
        self.assertIsNone(parse_answer("5", self.OPTS))

    def test_letters(self):
        self.assertEqual(parse_answer("a", self.OPTS), "N1")
        self.assertEqual(parse_answer("D", self.OPTS), "N4")
        self.assertIsNone(parse_answer("e", self.OPTS))

    def test_exact_label_case_insensitive(self):
        self.assertEqual(parse_answer("n3", self.OPTS), "N3")
        self.assertIsNone(parse_answer("n9", self.OPTS))

    def test_garbage_and_empty(self):
        self.assertIsNone(parse_answer("", self.OPTS))
        self.assertIsNone(parse_answer("banana", self.OPTS))
        self.assertIsNone(parse_answer("--", self.OPTS))


if __name__ == "__main__":
    unittest.main()