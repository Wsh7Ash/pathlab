"""Seeded prediction quiz: show the state before an algorithmic decision and
ask the learner to predict the decision itself.

- dijkstra / astar      -> "which node settles next?"
- bellman-ford          -> "which edge relaxes next?"
- floyd-warshall        -> "which pair improves next?"
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .algorithms import run_algorithm, Step
from .graph import Graph

QUESTION_ACTION = {
    "dijkstra": "settle",
    "astar": "settle",
    "bellman-ford": "relax",
    "floyd-warshall": "improve",
}
QUESTION_KIND = {
    "settle": "node",
    "relax": "edge",
    "improve": "node pair",
}
QUESTION_VERB = {
    "settle": "settles",
    "relax": "relaxes",
    "improve": "improves",
}


@dataclass
class Question:
    index: int
    algo: str
    action: str                 # the decision being predicted
    prompt: str                 # e.g. "Which node settles next?"
    context: str                # state BEFORE the decision (settled/frontier/dist)
    options: list[str]
    answer: str                 # correct option label
    after_step: int             # seq of the decision step (for tie-breaking display)

    @property
    def answer_index(self) -> int:
        return self.options.index(self.answer)

    def format(self) -> str:
        lines = [f"Q{self.index + 1}. {self.prompt}", self.context, ""]
        for i, opt in enumerate(self.options, start=1):
            lines.append(f"  {i}) {opt}")
        return "\n".join(lines)


@dataclass
class QuizResult:
    questions: list[Question]
    picks: list[str | None] = field(default_factory=list)
    correct: int = 0
    score_pct: float = 0.0
    passed: bool = False

    def report(self) -> str:
        lines = []
        for q, pick in zip(self.questions, self.picks):
            mark = "OK  " if pick == q.answer else "MISS"
            given = pick if pick is not None else "(no answer)"
            lines.append(f"  {mark} Q{q.index + 1}: you said {given!r}, "
                         f"answer was {q.answer!r}")
        lines.append(f"score: {self.correct}/{len(self.questions)} "
                     f"({self.score_pct:g}%) — "
                     + ("PASS" if self.passed else "FAIL"))
        return "\n".join(lines)


def _focus(step: Step) -> str:
    if step.edge:
        return f"{step.edge[0]}->{step.edge[1]}"
    return step.node or ""


def _context(step: Step) -> str:
    lines = [
        f"  settled:  {', '.join(step.settled) or '(none)'}",
        f"  frontier: {', '.join(step.frontier) or '(none)'}",
    ]
    if step.dist:
        dist = ", ".join(f"{k}={_fmt(v)}" for k, v in step.dist.items())
        lines.append(f"  dist:     {dist}")
    return "\n".join(lines)


def _fmt(v: float) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def _candidate_pool(graph: Graph, algo: str) -> list[str]:
    if QUESTION_ACTION[algo] == "settle":
        return graph.nodes
    arcs = [f"{u}->{v}" for u, v, _w in graph.arcs()]
    if QUESTION_ACTION[algo] == "relax":
        return sorted(set(arcs))
    return [f"{a}->{b}" for a in graph.nodes for b in graph.nodes if a != b]


def build_questions(graph: Graph, algo: str, start: str | None = None,
                    goal: str | None = None, count: int = 5, seed: int = 11,
                    options: int = 4) -> list[Question]:
    if count < 1:
        raise ValueError("questions must be >= 1")
    if options < 2:
        raise ValueError("options must be >= 2")
    action = QUESTION_ACTION[algo]
    result = run_algorithm(graph, algo, start=start, goal=goal)
    targets = [s for s in result.steps if s.action == action]
    if len(targets) < 2:
        raise ValueError(
            f"graph too small for a {algo} quiz: only {len(targets)} "
            f"{action} event(s)")

    # spread questions evenly across the decision sequence
    n = min(count, len(targets))
    picks = []
    if n == len(targets):
        picks = targets
    else:
        step_width = (len(targets) - 1) / (n - 1) if n > 1 else 0
        seen = set()
        for i in range(n):
            j = round(i * step_width)
            while j in seen and j + 1 < len(targets):
                j += 1
            seen.add(j)
            picks.append(targets[j])
        picks.sort(key=lambda s: s.seq)

    rng = random.Random(seed)
    pool = _candidate_pool(graph, algo)
    questions: list[Question] = []
    for qi, target in enumerate(picks):
        state = result.steps[target.seq - 1] if target.seq > 0 else target
        correct = _focus(target)
        distractors = [c for c in pool if c != correct]
        rng.shuffle(distractors)
        want = min(options, len(distractors) + 1)
        # prefer distractors the learner was just staring at
        live = [_focus(s) for s in result.steps[state.seq:target.seq]
                if _focus(s) != correct]
        ordered = [d for d in distractors if d in live]
        ordered += [d for d in distractors if d not in ordered]
        chosen = ordered[:want - 1]
        opts = chosen + [correct]
        rng.shuffle(opts)
        prompt_kind = QUESTION_KIND[action]
        questions.append(Question(
            index=qi, algo=algo, action=action,
            prompt=(f"After step {state.seq} ({state.action}), which "
                    f"{prompt_kind} {QUESTION_VERB[action]} next?"),
            context=_context(state),
            options=opts,
            answer=correct,
            after_step=target.seq,
        ))
    return questions


def grade(questions: list[Question], picks: list[str | None],
          pass_pct: float = 70.0) -> QuizResult:
    if len(picks) != len(questions):
        raise ValueError(f"expected {len(questions)} answers, got {len(picks)}")
    correct = sum(1 for q, p in zip(questions, picks) if p == q.answer)
    pct = round(correct * 100.0 / len(questions), 1) if questions else 0.0
    return QuizResult(
        questions=questions, picks=picks, correct=correct,
        score_pct=pct, passed=bool(questions) and pct >= pass_pct)


def parse_answer(line: str, options: list[str]) -> str | None:
    """Accept '3' (1-based), 'c' (option letter) or the exact label."""
    raw = line.strip()
    if not raw:
        return None
    if raw.isdigit():
        i = int(raw) - 1
        return options[i] if 0 <= i < len(options) else None
    if len(raw) == 1 and raw.isalpha():
        i = ord(raw.lower()) - ord("a")
        if 0 <= i < len(options):
            return options[i]
    for opt in options:
        if opt.lower() == raw.lower():
            return opt
    return None