"""Round 5: can activity learn neighbour relationships and per-tap observation filters?

A new local nearest-predecessor rule is compared with Fable's original News rule.
No new units and no change to the original oscillator. Every connection holds 16
learned tap coefficients in the optional trigger route. All weights freeze for test.

Run: python experiments/tap_learning_round5.py
Output: results/tap_learning_round5.json
"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
from gn.core import Colony, G, QMIN
from gn.rules import pace
from cue import N, OFF, tick, probe, score, teach

SEEDS, TRIALS, THETA, REFRACTORY = 12, 8, 0.25, True


def learn(seed):
    """Local credit: closest preceding presynaptic beat, then tap onsets.

    A postsynaptic beat credits a preceding presynaptic beat 1..5 ticks earlier.
    Each selected edge learns which taps switched on within 1..8 ticks before
    that postsynaptic beat, correcting for spontaneous tap-onset frequency.
    An engineered gain maps a ~0.5 predecessor fraction to ~0.22, to compare
    with the previous hand-set chain. The gains are NOT learned.
    """
    c = Colony(N, w=np.full((N, N), 0.02) * OFF, rng=np.random.default_rng(seed))
    last_beat = np.full(N, -999, dtype=int)
    before_beat = np.zeros(N, bool)
    last_tap = np.full((N, 16), -999, dtype=int)
    before_tap = np.zeros((N, 16), bool)
    credits = np.zeros((N, N))
    correlation = np.zeros((N, N, 16))
    tap_events = np.zeros((N, 16))
    post_events = np.zeros(N)

    for direction in ["A", "B"] * 8:
        paced = pace(N, [0, 1, 2, 3] if direction == "A" else [3, 2, 1, 0])
        for _ in range(500):
            c.step(force=paced(c.t))
            t = c.t
            active = G[c.q - QMIN] > 0.5
            switched_on = active & ~before_tap
            before_tap = active
            last_tap[switched_on] = t
            tap_events += switched_on
            beating = c.own > 3.0
            onset = beating & ~before_beat
            before_beat = beating
            for dst in np.flatnonzero(onset):
                post_events[dst] += 1
                age = t - last_beat
                age[dst] = 999
                candidates = np.where((age >= 1) & (age <= 5))[0]
                if len(candidates):
                    src = int(candidates[np.argmin(age[candidates])])
                    credits[dst, src] += 1
                    tap_age = t - last_tap[src]
                    correlation[dst, src] += (tap_age >= 1) & (tap_age <= 8)
            last_beat[onset] = t

    for _ in range(1500):
        c.step()  # Cooldown without changing any learned matrix.

    fraction = credits / np.maximum(post_events[:, None], 1)
    weights = np.clip(0.02 + 0.4 * fraction, 0.02, 0.35)
    np.fill_diagonal(weights, 0)

    related = correlation / np.maximum(credits[:, :, None], 1)
    background = np.minimum(1.0, 8 * tap_events / 8000)
    skill = np.maximum(0, related - background[None, :, :])
    salience = skill**4
    denominator = salience.sum(axis=2, keepdims=True)
    mixture = np.divide(salience, denominator,
                        out=np.zeros_like(salience), where=denominator > 0)
    # The filter is a vector of coefficients on all sixteen taps.
    # Gain 2 matches the two-tap 0+1 trigger's nominal amplitude.
    filter16 = 2 * weights[:, :, None] * mixture
    return c, weights, filter16, fraction, skill


def fixed_taps(weights, indices):
    filt = np.zeros((N, N, 16))
    for index in indices:
        filt[:, :, index] = weights
    return filt


def ideal_weights():
    w = np.full((N, N), 0.02) * OFF
    for i in range(3):
        w[i, i + 1] = w[i + 1, i] = 0.22
    return w


def shuffled_taps(filt, seed):
    out = filt.copy()
    rng = np.random.default_rng(3000 + seed)
    for i in range(N):
        for j in range(N):
            if i != j:
                out[i, j] = out[i, j, rng.permutation(16)]
    return out


def shuffled_edges(weights, filt, seed):
    p = np.random.default_rng(4000 + seed).permutation(N)
    return weights[np.ix_(p, p)].copy(), filt[np.ix_(p, p)].copy()


def measure(col, filt):
    if filt is None:
        a, na = probe(col, 0, THETA, REFRACTORY)
        b, nb = probe(col, 3, THETA, REFRACTORY)
        z, nz = probe(col, None, THETA, REFRACTORY)
    else:
        a, na = probe(col, 0, THETA, REFRACTORY, trigger_filter=filt)
        b, nb = probe(col, 3, THETA, REFRACTORY, trigger_filter=filt)
        z, nz = probe(col, None, THETA, REFRACTORY, trigger_filter=filt)
    return {
        "cue0_0123": int(score(a, 0)[1]),
        "cue3_3210": int(score(b, 3)[1]),
        "sham_0123": int(score(z, 0)[1]),
        "sham_3210": int(score(z, 3)[1]),
        "cue0_wrong": int(score(a, 3)[1]),
        "cue3_wrong": int(score(b, 0)[1]),
        "beats_cue0": na,
        "beats_cue3": nb,
        "beats_no_cue": nz,
    }


def evaluate(base, weights, filt):
    col = copy.deepcopy(base)
    col.w = weights.copy()
    for _ in range(600):
        tick(col, THETA, REFRACTORY, trigger_filter=filt)
    rows = []
    for _ in range(TRIALS):
        for _ in range(173):
            tick(col, THETA, REFRACTORY, trigger_filter=filt)
        rows.append(measure(col, filt))
    return rows


def summarize(by_seed):
    rows = [row for group in by_seed for row in group]
    means = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    for direction, cue in (("0123", "cue0_0123"), ("3210", "cue3_3210")):
        sham = "sham_" + direction
        means["cue_advantage_" + direction] = means[cue] - means[sham]
        rng = np.random.default_rng(20261110)
        boot = []
        for _ in range(1000):
            selected = rng.integers(0, SEEDS, SEEDS)
            boot.append(float(np.mean(
                [r[cue] - r[sham] for idx in selected for r in by_seed[idx]])))
        means["cue_advantage_" + direction + "_seed_bootstrap95"] = [
            float(x) for x in np.quantile(boot, [0.025, 0.975])]
    means["n"] = len(rows)
    return means


def main():
    labels = (
        "fable_AB", "ideal_chain", "nearest_fixed_01", "nearest_fixed_67",
        "nearest_learned_taps", "nearest_shuffled_taps", "nearest_shuffled_edges",
    )
    result_rows = {name: [] for name in labels}
    learned_stats = []
    for seed in range(SEEDS):
        base, weights, filt, fractions, skill = learn(seed)
        fable = teach("AB", seed)
        p = np.random.default_rng(4000 + seed).permutation(N)
        cases = {
            "fable_AB": (fable, fable.w, None),
            "ideal_chain": (base, ideal_weights(), None),
            "nearest_fixed_01": (base, weights, None),
            "nearest_fixed_67": (base, weights, fixed_taps(weights, (6, 7))),
            "nearest_learned_taps": (base, weights, filt),
            "nearest_shuffled_taps": (base, weights, shuffled_taps(filt, seed)),
            "nearest_shuffled_edges": (base, *shuffled_edges(weights, filt, seed)),
        }
        for name, (col, w, obs) in cases.items():
            result_rows[name].append(evaluate(col, w, obs))
        adjacent = [(i, j) for i in range(4) for j in range(4) if abs(i - j) == 1]
        shortcuts = [(i, j) for i in range(4) for j in range(4) if abs(i - j) > 1]
        learned_stats.append({
            "adjacent_mean": float(np.mean([weights[i, j] for i, j in adjacent])),
            "shortcut_mean": float(np.mean([weights[i, j] for i, j in shortcuts])),
            "tap_ranking_for_edge_0_to_1": list(np.argsort(-skill[1, 0])[:6].astype(int)),
            "edge_matrix_first4": weights[:4, :4].round(5).tolist(),
        })
        print("seed", seed, "adjacent", round(learned_stats[-1]["adjacent_mean"], 3),
              "shortcut", round(learned_stats[-1]["shortcut_mean"], 3), flush=True)

    output = {
        "spec": {
            "seeds": SEEDS, "trials_per_seed": TRIALS, "cue_window": 40,
            "trigger_threshold": THETA, "refractory_ticks": 10,
            "training": "A/B alternating 16 x 500 ticks; cooldown 1500; freeze test weights",
            "nearest_predecessor_window_ticks": [1, 5],
            "tap_post_window_ticks": [1, 8],
            "hand_set_credit_scale": 0.4,
            "learned_filter_gain": 2,
            "caveat": "New engineered nearest-predecessor rule. Tap weights influence only optional trigger at test, not original controller during experience.",
        },
        "conditions": {name: summarize(result_rows[name]) for name in labels},
        "learning": {
            "mean_adjacent_weight": float(np.mean([r["adjacent_mean"] for r in learned_stats])),
            "mean_shortcut_weight": float(np.mean([r["shortcut_mean"] for r in learned_stats])),
            "per_seed": learned_stats,
        },
    }
    path = ROOT / "results" / "tap_learning_round5.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, indent=2))
    print("RESULTS", json.dumps(output), flush=True)


if __name__ == "__main__":
    main()
