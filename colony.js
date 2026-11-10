// The colony, in the browser. Same arithmetic as gn/core.py and gn/rules.py (checked by tests/parity.js).
const S_SET = 0.6, TARGET = 0.1, O0 = 0.8739509815096245, LOUD = 3.0, BEAT = -0.28, WIN = 50, DELAY = 4;

function qOf(o) { if (o === 0) o = 0.1; return Math.max(QMIN, Math.min(QMAX, Math.trunc(5 + 50 * o))); }
function damp(r) { return S_SET + (2 / (1 + Math.exp(-3 * (r - S_SET))) - 1) / 3; }
function amplify(r, v) { return S_SET + Math.tanh(2 * (r - S_SET) * (1 + 10 * Math.abs(v - TARGET))); }

class Colony {
  constructor(n, opts = {}) {
    this.n = n; this.t = 0; this.kind = opts.kind || 'news';
    this.eta = 0.0005; this.cap = 0.6; this.tau = 3; this.scale = 0.9995; this.patience = 130;
    const rnd = opts.random ? Math.random : null;
    this.w = []; this.heard = []; this.pipe = []; this.hist = []; this.lastHeard = [];
    for (let i = 0; i < n; i++) {
      this.w.push(Array.from({ length: n }, (_, j) => (i === j ? 0 : 0.02)));
      this.heard.push(new Array(n).fill(0));
      this.lastHeard.push(new Array(n).fill(-999));
      this.pipe.push(rnd ? Array.from({ length: DELAY }, () => 0.3 + 0.7 * rnd())
        : (opts.pipe ? opts.pipe[i].slice() : [null, null, null, O0]));
      this.hist.push(rnd ? Array.from({ length: WIN }, () => 1.6 * rnd()) : []);
    }
    this.count = rnd ? WIN : 0;
    this.q = new Array(n).fill(0); this.own = new Array(n).fill(0); this.R = new Array(n).fill(0);
    this.varc = new Array(n).fill(0); this.mode = new Array(n).fill(1);
    this.lastBeat = new Array(n).fill(0); this.writes = 0; this.wrote = [];
  }

  step(force) {
    const n = this.n, qh = new Array(n);
    for (let i = 0; i < n; i++) {
      const src = this.pipe[i][0], live = src !== null;
      this.q[i] = live ? qOf(src) : qOf(0);
      qh[i] = live ? this.q[i] : QMAX;
      this.own[i] = live ? T0[this.q[i] - QMIN] : 0;
    }
    this.count++;
    for (let i = 0; i < n; i++) {
      let R = 0;
      for (let j = 0; j < n; j++) {
        this.heard[i][j] = i === j ? 0 : T6[qh[j] - QMIN];
        R += this.w[i][j] * this.heard[i][j];
      }
      R = this.own[i] + R; this.R[i] = R;
      const h = this.hist[i]; h.push(R); if (h.length > WIN) h.shift();
      let v = 0;
      if (this.count > 10) {
        let m = 0; for (const x of h) m += x; m /= h.length;
        for (const x of h) v += (x - m) * (x - m); v /= h.length;
      }
      this.varc[i] = v;
      const hot = v > TARGET;
      this.mode[i] = hot ? -1 : 1;
      let o = hot ? damp(R) : amplify(R, v);
      if (force && force[i] !== null && force[i] !== undefined) o = force[i];
      this.pipe[i].shift(); this.pipe[i].push(o);
    }
    this.t++;
    this.learn();
  }

  learn() {
    const n = this.n; this.wrote = [];
    for (let i = 0; i < n; i++) if (this.own[i] > LOUD) this.lastBeat[i] = this.t;
    if (this.kind === 'none') return;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        const loud = this.heard[i][j] > LOUD;
        let wr = false;
        if (this.kind === 'news') wr = loud && this.mode[i] === 1;
        else {
          if (loud) this.lastHeard[i][j] = this.t;
          wr = (this.t - this.lastHeard[i][j] <= this.tau) && (this.t - this.lastBeat[i] <= this.tau)
            && (loud || this.own[i] > LOUD);
        }
        if (wr) { this.w[i][j] = Math.min(this.w[i][j] + this.eta, this.cap); this.writes++; this.wrote.push([i, j]); }
      }
    }
    for (let i = 0; i < n; i++) {
      if (this.t - this.lastBeat[i] > this.patience) for (let j = 0; j < n; j++) this.w[i][j] *= this.scale;
    }
  }

  // order held in the weights among units 0-3: follower<-leader minus leader<-follower (positive = order A)
  order() {
    let s = 0;
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) if (i > j) s += this.w[i][j]; else if (i < j) s -= this.w[i][j];
    return s / 6;
  }
}

function paceForce(n, order, t, period = 57, gap = 3) {
  const f = new Array(n).fill(null), ph = t % period;
  order.forEach((u, r) => { if (ph === r * gap || ph === r * gap + 1) f[u] = BEAT; });
  return f;
}
function seizureForce(n, t, period = 20) { return t % period < 2 ? new Array(n).fill(BEAT) : null; }

if (typeof module !== 'undefined') module.exports = { Colony, paceForce, seizureForce };
