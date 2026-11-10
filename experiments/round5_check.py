"""Check on round 5 (Fable, 10 November 2026).   python experiments/round5_check.py   (about 4 minutes)
Writes results/round5_check.json.

Sol's nearest-predecessor learner (tap_learning_round5.learn) is used unchanged. Two things vary:
  gap    ticks between taught beats (Sol used 3; the rule's window is 1-5)
  last   which order the final teaching block has (Sol's teaching ends on 3->2->1->0)
Readout: fixed taps 0-1, Sol's evaluate(), 12 starts x 8 probes.
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import tap_learning_round5 as T  # noqa: E402
from gn.rules import pace as PACE  # noqa: E402


def job(a):
    gap, swap, seed = a
    T.pace = lambda n, order: PACE(n, order[::-1] if swap else order, gap=gap)
    c, w, _, _, _ = T.learn(seed)
    adj = np.mean([w[i, i + 1] for i in range(3)] + [w[i + 1, i] for i in range(3)])
    short = np.mean([w[i, j] for i in range(4) for j in range(4) if abs(i - j) > 1])
    rows = T.evaluate(c, w, T.fixed_taps(w, [0, 1]))
    return [adj, short] + [float(np.mean([r[k] for r in rows]))
                           for k in ("cue0_0123", "cue3_3210", "sham_0123", "sham_3210")]


def main():
    out = []
    with Pool(4) as p:
        for gap, swap in [(3, False), (3, True), (1, False), (2, False), (4, False), (5, False),
                          (6, False), (8, False)]:
            R = np.array(p.map(job, [(gap, swap, s) for s in range(12)])).mean(0)
            row = dict(zip(("adjacent_weight", "shortcut_weight", "cue0_0123", "cue3_3210",
                            "no_cue_0123", "no_cue_3210"), map(float, R)))
            row.update(gap=gap, last_block="0123" if swap else "3210")
            out.append(row)
            print(json.dumps(row), flush=True)
    (ROOT / "results" / "round5_check.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
