// node tests/parity.js : the browser colony must reproduce the Python colony (numbers printed by tests/test_colony.py).
const taps = require('../taps.js'); Object.assign(global, taps);
const { Colony, paceForce } = require('../colony.js');
const N = 6, pipe = [];
for (let i = 0; i < N; i++) pipe.push([0, 1, 2, 3].map(k => 0.3 + 0.1 * i + 0.01 * k));
const c = new Colony(N, { kind: 'news', pipe });
let a = 0, b = 0;
for (let k = 0; k < 3000; k++) { c.step(paceForce(N, [0, 1, 2, 3], c.t)); a += c.own.reduce((x, y) => x + y, 0); }
for (let k = 0; k < 2000; k++) { c.step(null); b += c.own.reduce((x, y) => x + y, 0); }
const ws = c.w.flat().reduce((x, y) => x + y, 0);
console.log('JS', a.toFixed(6), b.toFixed(6), ws.toFixed(6), c.writes);
const ok = a.toFixed(4) === '20229.5794' && b.toFixed(4) === '12188.4703' && ws.toFixed(5) === '1.58914' && c.writes === 2959;
console.log(ok ? 'PARITY OK' : 'PARITY FAILED'); process.exit(ok ? 0 : 1);
