import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gn.core import Colony, beats, run  # noqa: E402
from gn.rules import Rule, pace, seizure  # noqa: E402

N = 6
OFF = ~np.eye(N, dtype=bool)


def taught(kind="news", seed=0):
    c = Colony(N, w=np.full((N, N), 0.02)*OFF, rng=np.random.default_rng(seed))
    rule = Rule(N, kind)
    run(c, 4000, force=pace(N, [0, 1, 2, 3]), rule=rule)
    run(c, 1500, rule=rule)
    return c, rule


class TestColony(unittest.TestCase):
    def test_single_unit_is_the_origin_loop(self):
        b = beats(run(Colony(1), 2000))[0]
        self.assertTrue(all(np.diff(b)[-10:] == 59))

    def test_reference_run_matches_the_browser(self):
        c = Colony(N, w=np.full((N, N), 0.02)*OFF)
        c.pipe = np.array([[0.3 + 0.1*i + 0.01*k for i in range(N)] for k in range(4)])
        rule = Rule(N, "news")
        a = run(c, 3000, force=pace(N, [0, 1, 2, 3]), rule=rule).sum()
        b = run(c, 2000, rule=rule).sum()
        self.assertAlmostEqual(a, 20229.579363, places=5)      # tests/parity.js checks the same numbers
        self.assertAlmostEqual(b, 12188.470338, places=5)
        self.assertEqual(rule.writes, 2959)

    def test_news_rule_writes_order(self):
        c, _ = taught()
        s = c.w[:4, :4]
        self.assertGreater(np.tril(s, -1).sum() - np.triu(s, 1).sum(), 0.2)

    def test_fast_seizure_does_not_write_but_slow_does(self):
        for period, check in ((20, lambda n: n < 30), (60, lambda n: n > 1000)):
            c, rule = taught()
            n0 = rule.writes
            run(c, 3000, force=seizure(N, period), rule=rule)
            self.assertTrue(check(rule.writes - n0), (period, rule.writes - n0))

    def test_hebb_writes_all_through_a_seizure(self):
        c, rule = taught("hebb")
        n0 = rule.writes
        run(c, 1000, force=seizure(N, 20), rule=rule)
        self.assertGreater(rule.writes - n0, 2000)


if __name__ == "__main__":
    unittest.main()
