"""Fourth round: can the existing dynamics replay a *given* bidirectional chain?

This is a representation-versus-dynamics control, not a learning result.
No new trigger, neuron, or rule: reuse cue.py's Q3 trigger, 10-tick refractory,
and the exact existing Colony.step() implementation. Freeze all weights.

Primary, specified in advance: adjacent bidirectional edges = 0.22,
others = 0.02, trigger threshold = 0.25, refractory = 10 ticks.
Evaluate learned two-order weights, ideal chain, permuted ideal chain, and
uniform weights on matched starting states, seeds 0..11, 8 trials each.
The score is the existing strict 40-tick first-onset-order score.

Run: python experiments/ideal_chain.py
Output: results/ideal_chain.json
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
from colony import N, OFF  # noqa: E402
from cue import teach, tick, probe, score  # noqa: E402

EDGE = 0.22
THETA = 0.25
SHORT_REFRACTORY = True
SEEDS = 12
TRIALS = 8


def ideal_weights():
    w = np.full((N, N), 0.02) * OFF
    for i in range(3):
        w[i, i + 1] = EDGE
        w[i + 1, i] = EDGE
    return w


def setup(base, condition, seed):
    c = copy.deepcopy(base)
    if condition == "ideal":
        c.w = ideal_weights()
    elif condition == "shuffled_ideal":
        p = np.random.default_rng(1000 + seed).permutation(N)
        w = ideal_weights()
        c.w = w[np.ix_(p, p)].copy()
    elif condition == "uniform":
        c.w = np.full((N, N), 0.02) * OFF
    elif condition == "learned_AB":
        pass
    else:
        raise ValueError(condition)
    return c


def measure(c):
    """Paired cue/no-cue probes from the same state; weights never update."""
    a, ba = probe(c, 0, THETA, SHORT_REFRACTORY)
    b, bb = probe(c, 3, THETA, SHORT_REFRACTORY)
    z, bz = probe(c, None, THETA, SHORT_REFRACTORY)
    return {
        "cue0_0123": int(score(a, 0)[1]),
        "cue3_3210": int(score(b, 3)[1]),
        "cue0_wrong_3210": int(score(a, 3)[1]),
        "cue3_wrong_0123": int(score(b, 0)[1]),
        "sham_0123": int(score(z, 0)[1]),
        "sham_3210": int(score(z, 3)[1]),
        "cue0_beats300": ba, "cue3_beats300": bb, "sham_beats300": bz,
    }


def summarize(rows):
    columns = list(rows[0][0])
    flat = [v for seed_rows in rows for v in seed_rows]
    summary = {k: float(np.mean([r[k] for r in flat])) for k in columns}
    for direction in ("0123", "3210"):
        key = "cue0_0123" if direction == "0123" else "cue3_3210"
        sham = "sham_" + direction
        summary["cue_advantage_" + direction] = summary[key] - summary[sham]
    # Bootstrap by seed, not by correlated snapshots within a seed.
    rng = np.random.default_rng(20261110)
    boot = {"0123": [], "3210": []}
    for _ in range(2000):
        chosen = rng.integers(0, len(rows), len(rows))
        sample = [v for index in chosen for v in rows[index]]
        for direction, key in (("0123", "cue0_0123"), ("3210", "cue3_3210")):
            boot[direction].append(float(np.mean([r[key] - r["sham_" + direction] for r in sample])))
    for direction in boot:
        summary["cue_advantage_" + direction + "_seed_bootstrap95"] = [
            float(x) for x in np.quantile(boot[direction], [0.025, 0.975])
        ]
    summary["trials"] = len(flat)
    return summary


def main():
    conditions = ("learned_AB", "ideal", "shuffled_ideal", "uniform")
    records = {key: [] for key in conditions}
    for seed in range(SEEDS):
        # Train once per seed so comparisons start from precisely the same
        # post-training dynamical state. The three controls replace only w.
        base = teach("AB", seed)
        for condition in conditions:
            c = setup(base, condition, seed)
            for _ in range(600):
                tick(c, THETA, SHORT_REFRACTORY)
            seed_rows = []
            for trial in range(TRIALS):
                for _ in range(173):
                    tick(c, THETA, SHORT_REFRACTORY)
                seed_rows.append(measure(c))
            records[condition].append(seed_rows)
        print("seed", seed, "of", SEEDS - 1, "complete", flush=True)
    result = {
        "spec": {"edge": EDGE, "other_edge": 0.02, "theta": THETA,
                 "refractory_ticks": 10, "seeds": SEEDS, "trials_per_seed": TRIALS,
                 "window_ticks": 40, "probe_ticks": 300,
                 "note": "Ideal and shuffled weights are hand-set, not learned."},
        "conditions": {condition: summarize(rows) for condition, rows in records.items()},
    }
    path = ROOT / "results" / "ideal_chain.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print("RESULTS", json.dumps(result), flush=True)
    print("WROTE", path, flush=True)


if __name__ == "__main__":
    main()
