# ReturnToGeometricNeuron

**Live page: https://anttiluode.github.io/ReturnToGeometricNeuron/**

*10 November 2026. Built by Claude (Fable 5.2) at Antti's request. Follows [GeometricNeuronOriginReview](https://github.com/anttiluode/GeometricNeuronOriginReview), where the 2025 `ecg.json` loop was reduced to its mechanism: it beats when it forgets its last beat.*

**Question:** the loop is one excitable unit with no slow state. It is not a neuron and not a synapse. How close can a bunch of them get, if the wiring and the homeostasis are written by hand and only a separate slow state is left to experience?

**Answer:** closer than one unit, in one specific way. Wire six of the loops together through the splitter outputs the original never used, and let experience write the `learned_weight` field that every edge in `ecg.json` already had. With one hand-written rule, *an edge grows only when the listener hears a beat while it has forgotten its own*, the colony:

- writes the order of its experience into its weights,
- does not write during a seizure of any length, as long as the seizure is faster than the units' forgetting time,
- comes out of the seizure out of step again, with the order still in the weights.

Without a slow state the same colony is locked in step for good by one common beat. With an ordinary coincidence (Hebb) rule the seizure writes every edge until every unit is silent.

Nothing is trained. There is no gradient anywhere.

## The one idea

The 50-sample window that makes the pulse is a refractory period: while a beat is remembered, no new beat can start. The same variable can be the gate for learning. While a unit remembers a beat, a beat it hears is not news. In a seizure every unit remembers a beat at every moment, so the gate stays shut on its own.

That predicts where the protection must end: at a common rhythm slow enough for the units to forget between pulses. It does.

| Seizure period (ticks) | 10 | 20 | 30 | 40 | 50 | 55 | 60 | 70 | 90 |
|---|---|---|---|---|---|---|---|---|---|
| Writes in 4,000 ticks of seizure | 5 | 5 | 17 | 17 | 5 | 5 | 6,372 | 6,525 | 6,213 |
| Units still beating afterwards (of 6) | 5.4 | 5.5 | 5.1 | 5.3 | 5.4 | 5.4 | 1.8 | 0.5 | 2.8 |

The forgetting time of a unit is 50 to 59 ticks. The line falls between 55 and 60.

## What was built

- `gn/core.py`: the colony. Each unit is the reduced loop from the origin review, bit-exact for one unit (period 59). A unit hears itself through splitter outputs 0–3 as before, and hears a neighbour through outputs 6–9 times a weight.
- `gn/rules.py`: the slow state. The **news** rule above; a **hebb** rule for comparison (write when a heard beat and an own beat fall within 3 ticks); and **scaling** (a unit silent for 130 ticks shrinks all its incoming weights together until it beats).
- `experiments/colony.py`: the three experiments below. `results/colony.json`: every number.
- `index.html`, `colony.js`, `taps.js`: the live page. Same arithmetic as the Python, checked to six decimals by `tests/parity.js`.

## Results

**C1. What one edge does.** Listening unit, speaking unit, one edge, 16 random starts per weight.

| Weight | Listening on outputs 6–9 | Listening on outputs 0–3 |
|---|---|---|
| 0.01 – 0.02 | ignored | ignored |
| 0.05 – 0.2 | locked at a fixed lag; several lags are stable | locked; up to 7 stable lags |
| 0.3 – 0.5 | silenced | locked, mostly at lag 0 |
| 1.0 | silenced | silenced |

A heard beat enters the listener's memory like its own, so a strong edge makes the listener refractory. There is only this one sign. Where on the surface the listener sits matters: at the moment a unit is blind to itself (square size 78–84, its own outputs read 0), outputs 6–9 read 3.75–4.0. A mid-row listener hears the beat coming four ticks early.

**C2. Experience, seizure, release.** Units 0–3 are made to beat in order (history A) or in reverse (B) for 4,000 ticks, left alone 1,500, forced to beat together every 20 ticks, then left alone 2,700. 12 random starts per history. "Order in the weights" is the mean weight follower←leader minus leader←follower, A minus B.

| | Frozen weights | Hebb | News |
|---|---|---|---|
| Order in the weights before the seizure | 0 | −0.05 | +0.20 |
| Weight change during a seizure of 1k / 4k / 16k ticks | 0 | 0.05 / 0.20 / 0.54 | 0.0001 / 0.0001 / 0.0001 |
| Order in the weights after release (1k seizure) | 0 | −0.03 | +0.13 |
| Same, with no seizure at all | 0 | −0.02 | +0.19 |
| History guessed from final weights (1k seizure) | 12 of 24 | 20 of 24 | 22 of 24 |
| Pairs beating identically after release | all | none | none |
| Units beating after a 16k seizure (of 6) | 6 | 0 | 5.5 |

Three things to read from it:

- The frozen colony does hold the order, in its timing alone (+0.78 / −0.76 from beat times), with no seizure. Any seizure sets that to exactly 0 and the six units are identical from then on.
- The news colony loses a third of its order (+0.20 → +0.13), but not in the seizure. The weights at the end of the seizure are unchanged. The loss comes in the recovery, when the units come out in step, forget together, and write each other while they drift apart.
- Hebb is not erased quickly. A seizure adds the same amount to every edge, so the pattern survives until the ceiling. Then everything is silent.

**C3. Where the protection ends.** The table at the top.

## Second round: timing, and the control that was missing

Sol (ChatGPT) read the code and raised two points. Both were right to raise. `experiments/phase.py`, numbers in `results/phase.json`.

**P1. One heard pulse at each of the 59 phases** of a lone, untrained unit. Entry: how many ticks later the next beat comes.

| Weight of the pulse | Effect |
|---|---|
| 0.05, 0.1 | none at any phase |
| 0.2 | none, except on 3 ticks in every 8 (phases 8–10, 16–18, 24–26, 32–34, 40–42), where the beat comes 55 ticks late |
| 0.3 | every phase from 6 to 51; alternates within each 8 ticks between "delay = phase" and "delay ≈ 55" |
| 0.5, 1.0 | delay = phase for phases 2–55: the unit restarts its clock from the heard beat. No effect in the last three ticks, when its own beat is already on the way |

So the loop already gates input by arrival time, on two scales: the 59-tick cycle and an 8-tick ripple inside it (8 is twice the loop delay; that it is the idle ripple is my reading, not tested by varying the delay). A pulse never advances the beat. There is still only one sign.

**P2. Is recovery owed to learning or only to unequal weights?** Each learned weight set, frozen, against the same set with unit labels shuffled, frozen. 1,000-tick seizure, 12 starts per history.

| | Learned | Shuffled |
|---|---|---|
| Pairs beating identically after release | none | none |
| Order in the beats, A / B | +0.25 / −0.23 | +0.03 / −0.03 |
| Runs with the right order | 22 of 24 | 14 of 24 |

Falling out of step needs only inequality. The earlier claim about the frozen colony is narrowed accordingly: it applied to identical units. What learning adds is the order, and with weights held still it returns in the beating at nearly full strength (+0.29 / −0.25 before the seizure). The weaker figure in C2 (+0.14 / −0.10) came from the colony rewriting itself during recovery, not from the memory failing to show.

**P3. Direction of influence.** Weights frozen, one unit made to beat once, shift of each other unit's next beat measured against an untouched copy.

| | Leader → follower | Follower → leader | Runs where leader moves follower more |
|---|---|---|---|
| Learned | 14.2 ticks | 5.2 ticks | 22 of 24 |
| Shuffled | 14.4 ticks | 16.3 ticks | 12 of 24 |

Sol also noted that the C2 summaries for 1k, 4k and 16k seizures are identical. They are: the forcing is periodic and the colony is deterministic, so after the first few pulses nothing more changes. That is a repeatable regime of this model, and says little about a biological seizure.

**How the MIT theta study (Broschard et al., Cell Reports, Nov 2026) fits.** Only as a direction. It reports slow waves setting when faster activity can carry information, with the direction of influence between areas changing by task moment. P1 shows this loop has a slow cycle that gates input and a faster ripple nested in it; P3 shows learned, directed influence. Missing is the part that makes theirs cognition: the direction here is fixed by the weights and does not switch with what the colony is doing.

## How close to a neuron

| A neuron has | The colony has | Standing |
|---|---|---|
| Threshold, refractory period, reset | the forgetting clock | measured, one unit |
| Synapses that follow history | `learned_weight` under the news rule | measured, one task |
| Timing-dependent writing | an input before the beat is written, one after is not | resemblance only; nothing weakens a late edge |
| Scaling that keeps a quiet cell alive | silent units shrink their incoming weights | hand-written and too weak: at 4× the learning rate the colony dies (0.5 of 6 alive) |
| Excitation and inhibition | one sign: a heard beat quiets | missing |
| Dendrites, cable, graded response | nothing | missing; a push is still all or none |

## Ledger

**Shown**

- One unit of the colony is the origin loop (period 59). Browser and Python agree to six decimals over 5,000 ticks.
- The news rule writes order (+0.20 for A against B) and the history is read back from the weights after a seizure in 22 of 24 runs.
- Weight change in a fast seizure is 0.0001 at 1,000, 4,000 and 16,000 ticks.
- The protection ends at the forgetting time, as predicted before the run.
- A colony of identical units never leaves a seizure. Unequal weights suffice to break that (P2).
- With weights frozen, learned order returns in the beats after a seizure and influence is directed (P2, P3).
- The untrained loop gates a heard pulse by arrival phase (P1).

**Not shown**

- That the memory is useful. It has not been set against any task or any simple sequence-memory baseline.
- Selection: two stored orders, one cue, the colony following the cued one with weights unchanged. This is the next test.
- That it lasts. Ordinary life keeps writing; the order fades without any seizure.
- Unlearning. No rule makes a weight smaller for a reason.
- Scale. Six units, 12 starts per history, one task, one Hebb variant.
- A discovery about the gate. The gate was designed. What was measured is that this loop's own variance holds it shut through a seizure, and exactly where that stops.

## What it could become

In order of how much I would bet on each:

1. **A second sign.** Everything a unit hears goes into its memory and quiets it. A neighbour's beat routed into the *output* instead would trigger a beat (the origin review measured this: a −1 kick resets the clock). With both routes, the colony has excitation and inhibition, and the memory could show in behaviour instead of sitting in the weights.
2. **Geometry as the slow state.** The listening position on the surface (which splitter outputs an edge uses) decides whether a listener hears the beat or hears it coming. Letting that position move with experience would be the original 2025 idea, a surface with geometry, doing the learning. Not tried.
3. **A reason to shrink.** Without one, the colony can only fill up.

## Reproduce

```bash
python experiments/colony.py                 # about 6 minutes on 4 cores, writes results/colony.json
python experiments/phase.py                  # about 4 minutes, writes results/phase.json
python -m unittest discover -s tests -v      # 6 tests
node tests/parity.js                         # browser arithmetic against Python
python experiments/make_taps.py /path/to/GeometricNeuronOriginReview   # rebuilds gn/taps.json from the archived nodes
```

Details of the rules and the measures: [docs/NOTE.md](docs/NOTE.md).
