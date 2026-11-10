"""Two stored orders, one cue (10 November 2026).   python experiments/cue.py   (about 5 minutes)
Writes results/cue.json.

A colony is taught 0->1->2->3 only (A), 3->2->1->0 only (B), or both in alternating blocks (AB).
Weights are then frozen. One unit is made to beat once: unit 0 (the head of A) or unit 3 (the head
of B). Does the colony then beat in the cued order?

Q1  The colony as it is: a heard beat only enters the listener's memory and quiets it.
Q2  A second sign, written by hand and switched on at test time. The speaker's splitter outputs
    0-1 are silent except during a beat. If the weighted sum of them over a listener's edges
    exceeds theta, the listener's output is set to the beat value: it beats 5 ticks after the
    speaker. All or none. (A plain linear kick does not work: the checkerboard only gives a beat
    for square sizes between about -12 and 8, so too strong a kick overshoots into silence.)
Q3  Q2 plus a short refractory: a unit ignores triggers for 10 ticks after its own beat.
"""
import copy
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
from colony import N, OFF  # noqa: E402
from gn.core import G, QMIN, TARGET, Colony, run  # noqa: E402
from gn.rules import BEAT, Rule, pace  # noqa: E402

S2 = G[:, 0] + G[:, 1]                    # outputs 0-1: zero while idling and while blind, ~1.9 in a beat
SHORT = 10


def teach(kind, seed):
    c = Colony(N, w=np.full((N, N), 0.02)*OFF, rng=np.random.default_rng(seed))
    rule = Rule(N, "news")
    blocks = {"A": ["A"]*8, "B": ["B"]*8, "AB": ["A", "B"]*8}[kind]
    for b in blocks:
        run(c, 500, force=pace(N, [0, 1, 2, 3] if b == "A" else [3, 2, 1, 0]), rule=rule)
    run(c, 1500, rule=rule)
    return c


def tick(c, theta, refractory, force=None):
    """One step with the trigger route. Returns own readings."""
    if not hasattr(c, "last_own"):
        c.last_own = np.full(c.n, -999)
    if theta:
        drive = (c.w*S2[c.q - QMIN][None, :]).sum(axis=1)          # last tick's beats of the speakers
        fire = drive > theta
        if refractory:
            fire &= (c.t - c.last_own) >= SHORT
        trig = np.where(fire, BEAT, np.nan)
        force = trig if force is None else np.where(np.isnan(force), trig, force)
    own = c.step(force=force)
    c.last_own = np.where(own > 3, c.t, c.last_own)
    return own


def probe(c, cue, theta, refractory, window=40):
    """Cue one unit (or none), return first beat time of units 0-3 after the cue, and beat count."""
    c = copy.deepcopy(c)
    f = np.full(N, np.nan)
    if cue is not None:
        f[cue] = BEAT
    own = np.array([tick(c, theta, refractory, force=f if k < 2 else None) for k in range(300)])
    loud = own > 3
    onsets = loud & ~np.vstack([np.zeros((1, N), bool), loud[:-1]])
    first = [int(np.argmax(onsets[:window, u])) if onsets[:window, u].any() else None for u in range(4)]
    return first, int(onsets.sum())


def score(first, cue):
    """(head beats first and the other three follow within the window, exact chain order)."""
    chain = [0, 1, 2, 3] if cue == 0 else [3, 2, 1, 0]
    t = [first[u] for u in chain]
    if any(x is None for x in t):
        return 0.0, False
    ok = sum(t[k + 1] > t[k] for k in range(3))
    return float(all(x > t[0] for x in t[1:])), ok == 3


def job(a):
    kind, seed, theta, refractory = a
    c = teach(kind, seed)
    for _ in range(600):
        tick(c, theta, refractory)
    res = {"kind": kind, "s0": [], "s3": [], "full0": 0, "full3": 0, "none": [], "beats": [], "n": 0}
    for trial in range(8):
        for _ in range(173):
            tick(c, theta, refractory)
        for cue in (0, 3):
            first, nb = probe(c, cue, theta, refractory)
            s, full = score(first, cue)
            res[f"s{cue}"].append(s)
            res[f"full{cue}"] += int(full)
            res["beats"].append(nb)
        first, nb = probe(c, None, theta, refractory)
        res["none"].append([float(score(first, 0)[1]), float(score(first, 3)[1])])
        res["n"] += 1
    return res


def main():
    out = {}
    with Pool(4) as pool:
        for name, theta, refr in (("Q1_memory_route_only", 0.0, False), ("Q2_trigger_theta0.2", 0.2, False),
                                  ("Q3_theta0.15_refractory", 0.15, True), ("Q3_theta0.2_refractory", 0.2, True),
                                  ("Q3_theta0.25_refractory", 0.25, True)):
            out[name] = {}
            for kind in ("A", "B", "AB"):
                R = pool.map(job, [(kind, s, theta, refr) for s in range(12)])
                n = sum(r["n"] for r in R)
                res = {"cue0_head_first_all_follow": float(np.mean([np.mean(r["s0"]) for r in R])),
                       "cue3_head_first_all_follow": float(np.mean([np.mean(r["s3"]) for r in R])),
                       "cue0_runs_0123_exactly": sum(r["full0"] for r in R)/n,
                       "cue3_runs_3210_exactly": sum(r["full3"] for r in R)/n,
                       "no_cue_runs_0123_exactly": float(np.mean([np.mean(r["none"], axis=0)[0] for r in R])),
                       "no_cue_runs_3210_exactly": float(np.mean([np.mean(r["none"], axis=0)[1] for r in R])),
                       "beats_in_300_ticks_after_cue": float(np.mean([np.mean(r["beats"]) for r in R]))}
                out[name][kind] = res
                print(name, kind, json.dumps(res), flush=True)
    (ROOT / "results" / "cue.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    np.set_printoptions(precision=2, suppress=True, linewidth=160)
    for k in ("A", "AB"):
        print(k, "\n", teach(k, 0).w[:4, :4])
    main()
