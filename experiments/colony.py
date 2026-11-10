"""Return to the geometric neuron: what a colony of ecg.json loops can keep (10 November 2026).

Run from the repository root:   python experiments/colony.py        (about 6 minutes on 4 cores)
Writes results/colony.json.

C1  What a neighbour does. One unit listens to another through one edge of weight w.
C2  Experience, seizure, release. Six units. Four are made to beat in order 0,1,2,3 (history A)
    or 3,2,1,0 (history B). Then every unit is made to beat together for a while. Then nothing.
    Three colonies: weights frozen, written by the hebb rule, written by the news rule.
C3  Where the protection ends. The news colony again, seizures of different periods.
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from gn.core import Colony, beats, run  # noqa: E402
from gn.rules import Rule, pace, seizure  # noqa: E402

N, SEEDS = 6, 12
OFF = ~np.eye(N, dtype=bool)


def c1_job(a):
    tap, w, seed = a
    c = Colony(2, w=[[0, w], [0, 0]], tap=[[0, tap], [0, 0]], rng=np.random.default_rng(seed))
    b = beats(run(c, 8000)[5000:])
    bi, bj = b[0], b[1]
    if len(bi) < 3:
        return "silent", None
    lags = sorted({int(t - bj[bj <= t][-1]) for t in bi if (bj <= t).any()})
    return ("locked", lags[0]) if len(lags) == 1 else ("free", None)


def asym(w):
    """Mean weight follower<-leader minus leader<-follower among the four paced units (order A)."""
    s = w[:4, :4]
    return float(np.tril(s, -1).sum() - np.triu(s, 1).sum())/6


def follows(x, y):
    if len(x) == 0 or len(y) == 0:
        return 0.0
    return float(np.mean([np.any((t - y >= 1) & (t - y <= 8)) for t in x]))


def order_score(b):
    """From beat times alone: do higher-numbered paced units beat just after lower-numbered ones?"""
    return float(np.mean([follows(b[j], b[i]) - follows(b[i], b[j])
                          for i in range(4) for j in range(i + 1, 4)]))


def c2_job(a):
    kind, hist, seed, seiz, period = a
    c = Colony(N, w=np.full((N, N), 0.02)*OFF, rng=np.random.default_rng(seed))
    rule = Rule(N, kind)
    order = [0, 1, 2, 3] if hist == "A" else [3, 2, 1, 0]
    run(c, 4000, force=pace(N, order), rule=rule)              # experience
    b1 = beats(run(c, 1500, rule=rule)[-1200:])                # left alone
    w1, n1 = c.w.copy(), rule.writes
    if seiz:
        run(c, seiz, force=seizure(N, period), rule=rule)      # seizure
    w2, n2 = c.w.copy(), rule.writes
    run(c, 1500, rule=rule)                                    # release
    b3 = beats(run(c, 1200, rule=rule))
    same = [len(b3[i]) > 0 and np.array_equal(b3[i], b3[j]) for i in range(N) for j in range(i)]
    return {"hist": hist, "dw": float(np.abs(w2 - w1)[OFF].mean()), "writes": n2 - n1,
            "a1": asym(w1), "a2": asym(w2), "a3": asym(c.w), "o1": order_score(b1),
            "o3": order_score(b3), "sync": float(np.mean(same)),
            "alive": int(sum(len(x) > 0 for x in b3)), "w3": c.w[OFF].tolist()}


def loo(R):
    """Leave-one-out nearest-centroid guess of the history from the final weights."""
    X, y = np.array([r["w3"] for r in R]), np.array([r["hist"] == "B" for r in R])
    ok = 0
    for i in range(len(y)):
        m = np.arange(len(y)) != i
        cen = [X[m & (y == k)].mean(0) for k in (False, True)]
        ok += int(np.argmin([np.linalg.norm(X[i] - cc) for cc in cen]) == y[i])
    return ok/len(y)


def summarise(R):
    A, B = [r for r in R if r["hist"] == "A"], [r for r in R if r["hist"] == "B"]
    m = lambda k, S: float(np.mean([r[k] for r in S]))  # noqa: E731
    return {"weight_change_in_seizure": m("dw", R), "writes_in_seizure": m("writes", R),
            "order_in_weights_before": m("a1", A) - m("a1", B),
            "order_in_weights_end_of_seizure": m("a2", A) - m("a2", B),
            "order_in_weights_after": m("a3", A) - m("a3", B),
            "order_in_beats_before": [m("o1", A), m("o1", B)],
            "order_in_beats_after": [m("o3", A), m("o3", B)],
            "history_guessed_from_weights": loo(R), "pairs_beating_identically": m("sync", R),
            "units_alive_of_6": m("alive", R)}


def main():
    out = {}
    with Pool(4) as pool:
        c1 = {}
        for tap in (0, 6):
            for w in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0):
                res = pool.map(c1_job, [(tap, w, s) for s in range(16)])
                kinds = [r[0] for r in res]
                c1[f"tap{tap}_w{w}"] = {k: kinds.count(k) for k in ("free", "locked", "silent")}
                c1[f"tap{tap}_w{w}"]["lags"] = sorted({r[1] for r in res if r[0] == "locked"})
                print("C1", tap, w, c1[f"tap{tap}_w{w}"], flush=True)
        out["C1"] = c1
        c2 = {}
        for kind in ("none", "hebb", "news"):
            for seiz in (0, 1000, 4000, 16000):
                R = pool.map(c2_job, [(kind, h, s, seiz, 20) for h in "AB" for s in range(SEEDS)])
                c2[f"{kind}_seizure{seiz}"] = summarise(R)
                print("C2", kind, seiz, json.dumps(c2[f"{kind}_seizure{seiz}"]), flush=True)
        out["C2"] = c2
        c3 = {}
        for period in (10, 20, 30, 40, 50, 55, 60, 70, 90):
            R = pool.map(c2_job, [("news", h, s, 4000, period) for h in "AB" for s in range(SEEDS)])
            c3[str(period)] = summarise(R)
            print("C3", period, json.dumps(c3[str(period)]), flush=True)
        out["C3"] = c3
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "colony.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
