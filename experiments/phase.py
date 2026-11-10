"""What the existing geometry already does, and the control that was missing (10 November 2026).

Run from the repository root:   python experiments/phase.py        (about 4 minutes on 4 cores)
Writes results/phase.json.  Both parts were proposed by Sol (ChatGPT) after reading colony.py.

P1  Phase response of one unit. A single heard pulse of weight w arrives at each of the 59 phases
    of the cycle. How much later or earlier is the unit's next beat, against an untouched copy?
P2  The missing control. Is a colony's recovery from a seizure owed to what it learned, or only
    to its weights being unequal? Frozen colonies whose weights are a learned set with the unit
    labels shuffled, against the learned colonies themselves.
P3  Directed influence. In a taught colony with weights frozen, one unit is made to beat once.
    How far does that move each other unit's next beat? Leader -> follower against the reverse,
    and against the shuffled colonies.
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
from colony import N, OFF, order_score  # noqa: E402
from gn.core import S4, QMIN, Colony, beats, run  # noqa: E402
from gn.rules import BEAT, Rule, pace, seizure  # noqa: E402

HEARD_BEAT = float(S4[6, -9 - QMIN])          # what a mid-row listener reads of a forced beat


def next_beat(c, horizon=260):
    b = beats(run(c, horizon))[0]
    return int(b[0]) if len(b) else None


def p1_job(a):
    w, width = a
    base = Colony(1)
    run(base, 59*20)                           # on the cycle
    own = run(copy.deepcopy(base), 59)[:, 0]
    t_beat = int(np.argmax(own > 3))           # ticks until the next beat from `base`
    run(base, t_beat)                          # base now sits AT a beat: phase 0
    row = []
    for phase in range(59):
        ctl, tst = copy.deepcopy(base), copy.deepcopy(base)
        run(ctl, phase)
        run(tst, phase)
        ref = next_beat(ctl)
        pre = [tst.step(ext=np.array([w*HEARD_BEAT]))[0] for k in range(width)]
        b = beats(np.concatenate([pre, run(tst, 260)[:, 0]])[:, None])[0]   # beats during the pulse count
        row.append(int(b[0]) - ref if len(b) else None)
    return row


def learn(hist, seed):
    c = Colony(N, w=np.full((N, N), 0.02)*OFF, rng=np.random.default_rng(seed))
    rule = Rule(N, "news")
    run(c, 4000, force=pace(N, [0, 1, 2, 3] if hist == "A" else [3, 2, 1, 0]), rule=rule)
    run(c, 1500, rule=rule)
    return c


def shuffled(c, seed):
    """Same weights, unit labels permuted: equally unequal, but the order is scrambled."""
    p = np.random.default_rng(1000 + seed).permutation(N)
    c2 = copy.deepcopy(c)
    c2.w = c.w[np.ix_(p, p)].copy()
    return c2


def p2_job(a):
    hist, seed, cond = a
    c = learn(hist, seed)
    if cond == "shuffled":
        c = shuffled(c, seed)
    run(c, 1500)                                             # weights frozen from here on
    run(c, 1000, force=seizure(N, 20))
    run(c, 1500)
    b = beats(run(c, 1200))
    same = [len(b[i]) > 0 and np.array_equal(b[i], b[j]) for i in range(N) for j in range(i)]
    return {"hist": hist, "sync": float(np.mean(same)), "alive": int(sum(len(x) > 0 for x in b)),
            "order": order_score(b)}


def p3_job(a):
    hist, seed, cond = a
    c = learn(hist, seed)
    if cond == "shuffled":
        c = shuffled(c, seed)
    run(c, 1500)
    infl = np.zeros((N, N))                                  # infl[dst, src]: mean |shift| in ticks
    cnt = 0
    for trial in range(10):
        run(c, 37)
        ctl = copy.deepcopy(c)
        ref = [x[0] if len(x) else None for x in beats(run(ctl, 200))]
        for src in range(4):
            tst = copy.deepcopy(c)
            f = np.full(N, np.nan)
            f[src] = BEAT
            tst.step(force=f)
            tst.step(force=f)
            got = [x[0] + 2 if len(x) else None for x in beats(run(tst, 198))]
            for dst in range(4):
                if dst != src:
                    if ref[dst] is None or got[dst] is None:
                        infl[dst, src] += 0 if ref[dst] == got[dst] else 59
                    else:
                        infl[dst, src] += abs(got[dst] - ref[dst])
        cnt += 1
    infl /= cnt
    s = infl[:4, :4]
    fwd = float(np.tril(s, -1).sum()/6)      # low-numbered unit pulses, higher-numbered unit moves
    back = float(np.triu(s, 1).sum()/6)
    return {"hist": hist, "fwd": fwd, "back": back}


def main():
    out = {}
    with Pool(4) as pool:
        ws = (0.05, 0.1, 0.2, 0.3, 0.5, 1.0)
        p1 = {}
        for width in (2, 6):
            rows = pool.map(p1_job, [(w, width) for w in ws])
            for w, row in zip(ws, rows):
                p1[f"width{width}_w{w}"] = row
                vals = [r for r in row if r is not None]
                print("P1 width", width, "w", w, "silenced", row.count(None), "distinct shifts",
                      sorted(set(vals))[:12], "nonzero phases", sum(v != 0 for v in vals), flush=True)
                print("   ", row, flush=True)
        out["P1"] = p1
        m = lambda k, S: float(np.mean([r[k] for r in S]))  # noqa: E731
        for name, job in (("P2", p2_job), ("P3", p3_job)):
            out[name] = {}
            for cond in ("learned", "shuffled"):
                R = pool.map(job, [(h, s, cond) for h in "AB" for s in range(12)])
                A, B = [r for r in R if r["hist"] == "A"], [r for r in R if r["hist"] == "B"]
                if name == "P2":
                    res = {"pairs_beating_identically": m("sync", R), "units_alive_of_6": m("alive", R),
                           "order_in_beats_A": m("order", A), "order_in_beats_B": m("order", B),
                           "runs_with_right_sign": int(sum(r["order"] > 0 for r in A) + sum(r["order"] < 0 for r in B))}
                else:
                    res = {"A_low_to_high": m("fwd", A), "A_high_to_low": m("back", A),
                           "B_low_to_high": m("fwd", B), "B_high_to_low": m("back", B),
                           "runs_leader_moves_follower_more": int(sum(r["fwd"] > r["back"] for r in A)
                                                                  + sum(r["back"] > r["fwd"] for r in B))}
                out[name][cond] = res
                print(name, cond, json.dumps(res), flush=True)
    (ROOT / "results" / "phase.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
