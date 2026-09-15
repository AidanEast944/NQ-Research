"""
Single source of truth for how many independent strategy trials this project has run - used by
scorecard.py's Check 7 (Deflated Sharpe Ratio) so num_trials is never a hand-typed, driftable
literal scattered across call sites.

METHODOLOGY (fixed 2026-09-15 - see research_log.md's num_trials fix entry):
This used to count only numbered "## Entry N" headers in research_log.md and called that a
"conservative floor." That framing was backwards. DSR's benchmark (the expected best Sharpe you'd
see by chance alone) GROWS with num_trials - so UNDERcounting trials makes the benchmark too easy
to beat, which makes DSR look BETTER than it should, not more skeptical. Several log entries
collapse many real trials into one entry (e.g. an ATR-multiplier sweep, a 3-way volume-threshold
sweep, regime_filter_test.py's baseline-vs-filtered comparison) - counting entry headers alone
silently hid those, and the bias runs in the wrong direction for a "conservative" method to have.

Fixed by adding a second, independent count: actual run_scorecard() invocations across
src/research/*.py, sweep-loop-aware - a call inside `for x in [...]:` is multiplied by how many
values were swept (a 3-value ATR sweep wrapped around one run_scorecard() call counts as 3 trials,
not 1). num_trials is the MAX of this and the old entry-header count, never either one alone -
both are known undercounts in different directions (the entry count misses sweeps folded into one
entry; the AST count misses deleted/overwritten scripts, non-run_scorecard trials like
diagnostics/cointegration checks, and non-literal loop widths), so the max is the more skeptical,
more honest choice.

As of 2026-09-15 this does NOT change any currently-reported DSR number (both methods currently
resolve to 48 for this project - the entry-header count still happens to be the larger of the two,
since most of today's research_log.md entries didn't come from a run_scorecard()-based sweep). The
real fix is structural, not retroactive: before this change, no matter how large a future sweep
got, num_trials was invisibly capped at "however many entries have been logged" - a script could
run a 50-value parameter sweep through run_scorecard() and it would still only count as however
many log entries existed. Now a large sweep correctly pushes num_trials (and therefore the DSR
bar) up. Worth re-checking this module's output after any future large parameter sweep, since
that's exactly the case the old method silently mishandled.

Scope is deliberately src/research/*.py only, not the whole src/ tree. Production/monitoring
scripts (run_scorecards.py, the live *_forward_check.py trackers) re-score already-selected
strategies on fresh data - that's monitoring, not new hypothesis search, and counting those calls
too would double-count a strategy that was already counted once when it was originally researched.
"""
import ast
import os
import re


def _literal_len(node):
    """Length of a list/tuple/set/dict literal AST node, or None if it isn't one."""
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return len(node.elts)
    if isinstance(node, ast.Dict):
        return len(node.keys)
    return None


def _module_level_literals(tree):
    """Map top-level `NAME = [...]` / `{...}` assignments to their length, so a later
    `for x in NAME:` (or `NAME.items()`) can be resolved back to a real sweep width."""
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            n = _literal_len(node.value)
            if n is not None:
                out[node.targets[0].id] = n
    return out


def _count_scorecard_trials(tree, module_literals):
    total = 0

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.mult_stack = [1]

        def _iter_width(self, iter_node):
            target = iter_node
            # for x in some_dict.items()/.keys()/.values(): resolve to the dict itself
            if isinstance(target, ast.Call) and isinstance(target.func, ast.Attribute):
                if target.func.attr in ("items", "keys", "values"):
                    target = target.func.value
            n = _literal_len(target)
            if n is not None:
                return n
            if isinstance(target, ast.Name) and target.id in module_literals:
                return module_literals[target.id]
            # Unknown/runtime iterable (e.g. a computed date range) - don't inflate or deflate,
            # treat the loop body as a single trial rather than guessing its width.
            return 1

        def visit_For(self, node):
            width = self._iter_width(node.iter)
            self.mult_stack.append(self.mult_stack[-1] * width)
            self.generic_visit(node)
            self.mult_stack.pop()

        def visit_Call(self, node):
            nonlocal total
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else None
            )
            if name == "run_scorecard":
                total += self.mult_stack[-1]
            self.generic_visit(node)

    Visitor().visit(tree)
    return total


def count_scorecard_trials(research_dir=None):
    """Static count of actual run_scorecard() calls in src/research/*.py, sweep-loop-aware."""
    if research_dir is None:
        research_dir = os.path.join(os.path.dirname(__file__), "research")

    if not os.path.isdir(research_dir):
        raise FileNotFoundError(f"research directory not found at {research_dir}")

    total = 0
    for fn in sorted(os.listdir(research_dir)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(research_dir, fn)
        with open(path, "r", errors="ignore") as f:
            try:
                tree = ast.parse(f.read(), filename=path)
            except SyntaxError:
                continue
        literals = _module_level_literals(tree)
        total += _count_scorecard_trials(tree, literals)
    return total


def count_log_entries(log_path=None):
    """The old proxy, kept as a floor - see module docstring for why neither method alone is enough."""
    if log_path is None:
        log_path = os.path.join(os.path.dirname(__file__), "..", "research_log.md")

    if not os.path.exists(log_path):
        raise FileNotFoundError(
            f"research_log.md not found at {log_path} - num_trials cannot be determined. "
            "This is deliberate: silently falling back to a default would reintroduce the "
            "exact bug this function exists to fix."
        )

    with open(log_path, "r") as f:
        content = f.read()

    entries = re.findall(r"^## Entry (\d+):", content, re.MULTILINE)
    if not entries:
        raise ValueError(
            f"No '## Entry N:' headers found in {log_path} - num_trials cannot be determined."
        )

    return max(int(e) for e in entries)


def count_research_trials(log_path=None, research_dir=None):
    """
    num_trials for DSR (scorecard.py Check 7): the MAX of two independent undercounts.

    - count_log_entries(): number of logged research_log.md entries (misses sweeps folded into
      one entry).
    - count_scorecard_trials(): actual run_scorecard() call sites in src/research/*.py, sweep
      loops expanded (misses deleted/overwritten scripts and non-literal loop widths).

    Taking the max, rather than either alone, keeps num_trials moving in the direction that makes
    DSR MORE skeptical when the two disagree, never less - undercounting trials is the error this
    function exists to prevent, not something to risk reintroducing via a single fragile proxy.
    """
    return max(count_log_entries(log_path), count_scorecard_trials(research_dir))
