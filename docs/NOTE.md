# Note: rules, measures, provenance

*10 November 2026, Claude (Fable 5.2).*

## Provenance

`gn/taps.json` holds, for every square size q from −200 to 399, the first 16 values of the 256-vector that the archived `CheckerboardNode` and `ImageToVectorNode` produce. `experiments/make_taps.py` rebuilds it from a checkout of GeometricNeuronOriginReview. Outputs 0–3 summed give the table F that repository proved bit-exact against the full Perception Lab graph. `taps.js` is the same data for the page: sums of outputs 0–3 and of outputs 6–9.

Nothing in the wiring is foreign to Perception Lab. Its ports sum their incoming edges, the splitter has 16 outputs, and each saved edge has a `learned_weight` that multiplies the signal.

## One tick

For unit i, with pipeline delay d = 4 and window W = 50:

```
q_i   = int(5 + 50 * o_i(t-4))
own_i = sum of outputs 0-3 at q_i
R_i   = own_i + sum_j w_ij * (sum of outputs 6-9 at q_j)
var_i = variance of the last 50 values of R_i
o_i   = damp(R_i)            if var_i > 0.1     (the unit remembers a beat: "hot")
        amplify(R_i, var_i)  otherwise          (it has forgotten: "calm")
```

`damp` and `amplify` are the archived coupler's `edge_of_chaos` arithmetic with setpoint 0.6.

## The rules

A reading above 3.0 is "loud". Idle readings stay below 3; a beat is 3.47–3.88.

- **news:** each tick, for each edge j→i, if what i hears of j is loud and i is calm *after* this tick's reading has entered its window, then `w_ij += 0.0005`. No ceiling was needed in any run (a 0.6 cap exists in the code and was not reached).
- **hebb:** if a loud heard reading from j and a loud own reading of i both occurred within the last 3 ticks, `w_ij += 0.0005`, capped at 0.6.
- **scaling** (both): if i has not beaten for 130 ticks, all `w_i·` are multiplied by 0.9995 each tick.
- Initial weights 0.02 on every edge (the "ignored" range of C1).

Stimulation sets a unit's output to −0.28 for two ticks, which gives square size −9 and a full beat four ticks later. Experience: units in order, 3 ticks apart, every 57 ticks. Seizure: all units at once, every `period` ticks.

Because the gate is read after the heard reading enters the window, the news rule limits itself: once an edge is strong enough that the heard beat alone makes the listener hot, that edge stops growing.

## Measures

- **Order in the weights:** among units 0–3, the sum of w[i][j] for i > j minus the sum for i < j, divided by 6. Reported as history A minus history B.
- **Order in the beats:** for each pair i < j among units 0–3, the fraction of j's beats that fall 1–8 ticks after a beat of i, minus the converse; averaged. Reported for A and for B.
- **History guessed from weights:** leave-one-out nearest centroid on the 30 off-diagonal weights, 24 runs.
- **Pairs beating identically:** fraction of unit pairs whose beat times in the last 1,200 ticks are exactly equal.

## Things that went wrong on the way

- The first version of the news rule with a 20× larger rate and no scaling silenced the whole colony within 3,000 ticks. Scaling was added for that reason.
- With rate 0.002 and scaling 0.999 the news colony still died (0.5 of 6 units alive at the end). The published rates are four times slower. Aliveness is not robust.
- Why slow seizures write: between slow pulses each unit forgets and starts its own beat, and its neighbours, listening mid-row, hear the kick that precedes it while they are still calm.
