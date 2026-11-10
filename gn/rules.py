"""The slow state: two hand-written rules acting on ``learned_weight``. Nothing is trained.

news    (the proposal) an edge j -> i grows by eta each tick that unit i hears j loudly while i is
        still CALM, i.e. while i's own variance is below target: it has forgotten its last beat.
        The gate is the coupler's own ``regime`` output. No ceiling is needed.
hebb    (the comparison) an edge grows when a loud heard reading from j and a beat of i fall
        within tau ticks of each other, in either order. Ceiling at cap.
none    weights frozen.

scaling (all rules) a unit that has not beaten for `patience` ticks multiplies ALL its incoming
        weights by `scale` each tick until it beats again. Multiplying keeps the ratios.
"""
import numpy as np

LOUD = 3.0          # a heard or own reading above this is a beat (idle readings stay below 3)
BEAT = -0.28        # stimulation: output forced here for two ticks gives square size -9, a full beat


class Rule:
    def __init__(self, n, kind="news", eta=0.0005, cap=0.6, tau=3, scale=0.9995, patience=130):
        self.n, self.kind, self.eta, self.cap, self.tau = n, kind, eta, cap, tau
        self.scale, self.patience = scale, patience
        self.last_beat = np.zeros(n)
        self.last_heard = np.full((n, n), -999.0)
        self.writes = 0

    def __call__(self, c):
        loud, own_loud = c.heard > LOUD, c.own > LOUD
        self.last_beat[own_loud] = c.t
        if self.kind == "news":
            wr = loud & (c.mode[:, None] == 1)
        elif self.kind == "hebb":
            self.last_heard[loud] = c.t
            wr = (((c.t - self.last_heard) <= self.tau) & ((c.t - self.last_beat) <= self.tau)[:, None]
                  & (loud | own_loud[:, None]))
        else:
            wr = np.zeros((self.n, self.n), dtype=bool)
        np.fill_diagonal(wr, False)
        c.w[wr] = np.minimum(c.w[wr] + self.eta, self.cap)
        self.writes += int(wr.sum())
        if self.kind != "none" and self.scale < 1:
            quiet = (c.t - self.last_beat) > self.patience
            c.w[quiet] *= self.scale


def pace(n, order, period=57, gap=3):
    """Experience: the units in `order` are made to beat one after another, `gap` ticks apart."""
    def f(t):
        k = np.full(n, np.nan)
        ph = t % period
        for r, u in enumerate(order):
            if ph in (r*gap, r*gap + 1):
                k[u] = BEAT
        return k
    return f


def seizure(n, period=20):
    """Every unit is made to beat at the same tick, every `period` ticks."""
    return lambda t: np.full(n, BEAT) if t % period < 2 else np.full(n, np.nan)
