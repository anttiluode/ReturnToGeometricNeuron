"""A colony of the original ecg.json loops, wired to each other.

One unit is the REDUCED loop that GeometricNeuronOriginReview proved bit-exact against the
archived Perception Lab nodes:

    q_i(t)  = int(5 + 50 * o_i(t - d))               checkerboard square size, d = 4 ticks of pipeline
    taps    = G[q]                                   the 16 splitter outputs: the top row of the
                                                     16 x 16 picture of the checkerboard
    R_i(t)  = sum(taps_i[0:4])                       what the unit hears of ITSELF (the four wires
                                                     that ecg.json has)
            + sum_j  w_ij * sum(taps_j[a_ij : a_ij+4])   what it hears of unit j, through four
                                                     OTHER splitter outputs starting at tap a_ij
            + external input
    var_i   = variance of the last W values of R_i   W = 50
    o_i(t)  = damp(R_i) if var_i > 0.1 else amplify(R_i, var_i)

Nothing new is invented for the wiring. Perception Lab sums all edges into a port, the splitter
already has 16 outputs of which ecg.json used 4, and every edge in ecg.json already carries a
field called ``learned_weight`` (always 1.0, never written). ``w_ij`` is that field.

``taps.json`` was produced by the archived nodes themselves (see docs/NOTE.md, "Provenance").
"""
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
_D = json.loads((HERE / "taps.json").read_text())
QMIN, QMAX = _D["qmin"], _D["qmax"]
G = np.array(_D["taps"], dtype=np.float64)            # [q - QMIN, 16]
# S4[a, q - QMIN] = sum of four consecutive taps starting at a (a = 0 is the unit's own wiring)
S4 = np.stack([G[:, a:a + 4].sum(axis=1) for a in range(13)])

S, TARGET = 0.6, 0.1                                    # effective setpoint, target variance
O0 = 0.8739509815096245                                 # output saved in ecg.json


def q_of(o):
    o = np.where(o == 0, 0.1, o)                        # the node's `or 0.1`
    return np.clip(np.trunc(5 + 50*o).astype(int), QMIN, QMAX)


def damp(r):
    return S + (2/(1 + np.exp(-3*(r - S))) - 1)/3


def amplify(r, var):
    return S + np.tanh(2*(r - S)*(1 + 10*np.abs(var - TARGET)))


class Colony:
    """N coupled units. w[i, j] is the weight of the edge j -> i, tap[i, j] where i listens on j."""

    def __init__(self, n, w=None, tap=None, d=4, W=50, rng=None, lag=None):
        self.n, self.d = n, d
        self.W = np.full(n, W, dtype=int) if np.isscalar(W) else np.asarray(W, dtype=int)
        self.w = np.zeros((n, n)) if w is None else np.array(w, dtype=float)
        self.tap = np.full((n, n), 6, dtype=int) if tap is None else np.array(tap, dtype=int)
        self.lag = np.zeros((n, n), dtype=int) if lag is None else np.array(lag, dtype=int)
        self.maxlag = int(self.lag.max()) + 1
        self.L = int(self.W.max())
        self.hist = np.zeros((n, self.L))               # ring of readings, newest at column ptr-1
        self.count = 0
        self.pipe = np.full((d, n), np.nan)             # outputs in flight; nan = nothing yet
        self.pipe[-1] = O0
        if rng is not None:                             # random phases: a random amount of idling
            self.pipe = rng.uniform(0.3, 1.0, size=(d, n))
            self.hist = rng.uniform(0.0, 1.6, size=(n, self.L))
            self.count = self.L
        self.qlog = np.full((self.maxlag, n), q_of(np.array(O0)))   # recent q, for edge lags
        self.t = 0
        self.var = np.zeros(n)
        self.mode = np.ones(n, dtype=int)
        self.R = np.zeros(n)
        self.own = np.zeros(n)
        self.heard = np.zeros((n, n))                   # heard[i, j]: what i hears of j, unweighted
        self.q = np.zeros(n, dtype=int)

    def step(self, ext=None, kick=None, force=None):
        n = self.n
        src = self.pipe[0]
        live = ~np.isnan(src)
        q = q_of(np.where(live, src, 0.0))
        self.q = q
        own = np.where(live, S4[0, q - QMIN], 0.0)
        self.qlog = np.roll(self.qlog, 1, axis=0)
        self.qlog[0] = np.where(live, q, QMAX)          # QMAX is silent on every tap
        qj = self.qlog[self.lag, np.arange(n)[None, :]]             # [i, j]: q of j as i sees it
        heard = S4[self.tap, qj - QMIN]
        np.fill_diagonal(heard, 0.0)
        R = own + (self.w*heard).sum(axis=1)
        if ext is not None:
            R = R + ext
        self.hist[:, self.count % self.L] = R
        self.count += 1
        var = np.zeros(n)
        if self.count > 10:
            for i in range(n):                          # each unit has its own window length
                m = min(self.count, int(self.W[i]))
                idx = (self.count - 1 - np.arange(m)) % self.L
                var[i] = np.var(self.hist[i, idx])
        hot = var > TARGET
        o = np.where(hot, damp(R), amplify(R, var))
        if kick is not None:
            o = o + kick
        if force is not None:                           # stimulation: output set from outside (nan = leave)
            o = np.where(np.isnan(force), o, force)
        self.pipe = np.vstack([self.pipe[1:], o[None, :]])
        self.var, self.mode, self.R, self.own, self.heard = var, np.where(hot, -1, 1), R, own, heard
        self.t += 1
        return own


def run(col, ticks, ext=None, kick=None, rule=None, force=None):
    """Run and return own readings [ticks, n]. ext/kick/force: callables t -> array or None."""
    out = np.zeros((ticks, col.n))
    for k in range(ticks):
        out[k] = col.step(ext(col.t) if ext else None, kick(col.t) if kick else None,
                          force(col.t) if force else None)
        if rule is not None:
            rule(col)
    return out


def beats(own, thresh=3.0, gap=6):
    """Beat times per unit: first tick of each run of readings above thresh."""
    res = []
    for i in range(own.shape[1]):
        ts = np.flatnonzero(own[:, i] > thresh)
        keep = ts[np.insert(np.diff(ts) > gap, 0, True)] if len(ts) else ts
        res.append(keep)
    return res
