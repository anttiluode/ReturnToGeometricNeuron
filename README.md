# ReturnToGeometricNeuron

**Live page: https://anttiluode.github.io/ReturnToGeometricNeuron/**

*10 November 2026. Built by Claude (Fable 5.2) at Antti's request. Follows [GeometricNeuronOriginReview](https://github.com/anttiluode/GeometricNeuronOriginReview), where the 2025 `ecg.json` loop was reduced to its mechanism: it beats when it forgets its last beat.*

**Question:** the loop is one excitable unit with no slow state. It is not a neuron and not a synapse. How close can a bunch of them get, if the wiring and the homeostasis are written by hand and only a separate slow state is left to experience?

**Answer:** closer than one unit, in one specific way. Wire six of the loops together through the splitter outputs the original never used, and let experience write the `learned_weight` field that every edge in `ecg.json` already had. With one hand-written rule, *an edge grows only when the listener hears a beat while it has forgotten its own*, the colony:

- writes the order of its experience into its weights,
- does not write during a seizure of any length, as long as the seizure is faster than the units' forgetting time,
- comes out of the seizure out of step again, with the order still in the weights.

Without a slow state the same colony is locked in step for good by one common beat. With an ordinary coincidence (Hebb) rule the seizure writes every edge until every unit is silent.

There is **no gradient-based training**. The original News rule performs local, state-gated weight updates; the fifth/sixth-round nearest-predecessor rule instead counts **externally forced** teaching events and computes weights from those counts after teaching. That distinction is central to the evidence.

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

## Third round: two stored orders, one cue (not achieved)

`experiments/cue.py`, numbers in `results/cue.json`. A colony is taught 0→1→2→3 only, 3→2→1→0 only, or both in alternating blocks. Weights are frozen, then unit 0 or unit 3 is made to beat once. Entry: fraction of 96 trials in which units 0–3 then beat in exactly the cued order within 40 ticks.

| Colony | Taught | Cue 0 → 0123 | Cue 3 → 3210 | No cue: 0123 / 3210 | Beats in 300 ticks |
|---|---|---|---|---|---|
| As it was (heard beats only quiet) | one order | 0.09 | 0.08 | 0.10 / 0.08 | 28 |
| | both | 0.00 | 0.01 | 0.00 / 0.01 | 14 |
| Plus a trigger | one order | 0.06 | 0.05 | 0.09 / 0.05 | 138 |
| | both | 0.00 | 0.00 | 0.00 / 0.00 | 378 |
| Plus a trigger and a 10-tick refractory | one order | **0.51** | **0.49** | 0.38 / 0.34 | 34 |
| | both | 0.07 | 0.01 | 0.01 / 0.01 | 26 |

(One-order rows: the cue that matches the taught order. The mismatched cue gave 0.00 in every case. Trigger rows at threshold 0.2 without refractory and 0.25 with; thresholds 0.15 and 0.2 with refractory gave at most 0.07.)

What this says:

- **As it was, nothing.** A cue changes nothing measurable, as expected from one sign.
- **A trigger alone is a seizure.** A heard beat that makes the listener beat, with nothing to stop the echo, gives 5 to 27 times the normal number of beats.
- **Trigger plus a short refractory replays one stored order from its head**, about half the time, and never backwards. But the same replay happens unprompted in 34–38% of windows, because any natural beat of the head unit starts it. So the cue adds little; the order is in the colony's spontaneous activity already.
- **Two orders in one colony are not separable.** Selection failed at every threshold tried. The weights show why. Taught one order, the edge to the next unit in line is 0.14–0.23 and the edge two away is 0.04–0.11, so a threshold can pick out "next". Taught both, every edge among the four is 0.04–0.15 and "next" and "two away" overlap. The pairwise weights hold who-beat-near-whom and have no place to hold which order is meant.

Two facts about the geometry found on the way:

- Splitter outputs 0–1 read exactly zero while a unit idles and while it is blind, and 1.6–1.9 during a beat. Listening there gives a clean beat detector. Outputs 6–9 hear the lead-up as well.
- The checkerboard only gives a beat for square sizes between about −12 and 8. A push that is too strong overshoots (size −20 reads 1.67, not a beat). So a linear excitatory edge is a band-pass, and the trigger used here is a hand-written threshold instead.

The trigger and the refractory are hand-written additions that are not in `ecg.json`. They were switched on only at test time; the colony did not learn with them.

## Fourth round: ideal bidirectional chain isolates the missing capability

**Confirmed on GitHub Actions, 10 November 2026.** [Experiment](experiments/ideal_chain.py), [machine-readable results](results/ideal_chain.json), [verification workflow](.github/workflows/ideal-chain.yml).

The third round could not select two orders from learned weights. Does this mean the trigger/refractory dynamics cannot support it, or only that the News rule learned the wrong adjacency structure? We kept the **same six units, same trigger and 10-tick refractory, same trained starting states**; we froze weights throughout the probe. The only difference was the weight matrix.

Primary, set before running: immediate-neighbour edges bidirectional at 0.22, all other off-diagonal edges at 0.02; trigger threshold 0.25. Two endpoint cues (unit 0 or 3) and no-cue controls were tested from the same saved state. Strict success: first beats of units 0–3 appear in the specified order within 40 ticks. There were 12 starting seeds × 8 checkpoints = 96 paired trials per condition.

| Condition (weights frozen) | Cue 0: 0123 | Cue 3: 3210 | No cue: 0123 | No cue: 3210 |
|---|---:|---:|---:|---:|
| Learned AB | 7.3% | 1.0% | 1.0% | 1.0% |
| **Hand-set bidirectional chain** | **62.5%** | **67.7%** | 12.5% | 27.1% |
| Same ideal weights, shuffled unit labels | 6.3% | 1.0% | 4.2% | 0% |
| Uniform 0.02 | 2.1% | 0% | 1.0% | 0% |

Cue minus no-cue advantages for the ideal chain were **+50.0 percentage points** forward (seed-bootstrap 95% interval +39.6 to +61.5), **+40.6** reverse (+29.2 to +54.2). The cue did not produce the opposite exact sequence in either direction. All six existing Python tests passed in the workflow.

**Interpretation:** The existing trigger/refractory dynamics can express two directions with hand-specified local connectivity, and endpoint cues make them more likely. Thus the third-round failure does **not** prove that another context neuron is necessary. It exposes a representation/learning bottleneck: the News rule does not reliably produce the local bidirectional structure. This is **not** proof of learned two-sequence selection, because the successful weights were designed, not learned; endpoint cues are different inputs, not a general context switch; and exact replay remains imperfect and sometimes spontaneous.

**Next low-cost decision:** do not add theta or context units yet. Test whether learning *where an edge listens* (splitter tap index, which changes timing) can produce the required selectivity, with a frozen-tap and shuffled-tap comparison. Keep the ideal-chain score as the target, not an expectation.

## Fifth round: local predecessor learning and sixteen-tap filtering

**Completed and reproduced 10 November 2026.** [Code](experiments/tap_learning_round5.py) · [Numbers](results/tap_learning_round5.json) · [GitHub Actions](.github/workflows/tap-learning.yml).

The fourth round demonstrated that a hand-specified bidirectional chain was sufficient for cue-sensitive replay. The fifth round asks whether experience can construct that chain and whether the **location of observation** contributes beyond learning the edges.

We used exactly the six original ECG loops, their original geometry, and Fable's optional Q3 trigger with a 10-tick refractory. Training: sixteen alternating 500-tick A/B blocks, then 1,500 ticks without forcing. At each postsynaptic beat the **new engineered local rule** credits only the *nearest preceding* observed presynaptic beat if it occurred 1–5 ticks earlier, thus discouraging shortcuts. A separate 16-coefficient-per-edge filter is formed from how often a tap switched on 1–8 ticks before that postsynaptic beat, subtracting each tap's ordinary onset frequency. The edge gain was **hand calibrated** as `0.02 + 0.4 × predecessor_fraction`, with a cap of 0.35; the tap-filter readout uses 2× gain. We neither added neurons nor used backpropagation, but the temporal window and gain were engineered, not discovered. The new filter is activated only during testing, not during learning.

Average directed edge strength: **0.1976** for six adjacent links among units 0–3, versus **0.0319** for the six non-adjacent shortcuts. The top observed taps on edge 0→1 were consistently **0, 1, 7, 6**, then 2 and 12—both the clean-beat and anticipatory channels, not predominantly idle channels.

After freezing all learned coefficients, we compared 12 seeds × 8 checkpoints = 96 paired trials per condition. A cue forces a two-tick beat at unit 0 or 3. A strict success requires the first observed beats of units 0–3 to occur in order within 40 ticks.

| Frozen test condition | Cue 0: 0123 | Cue 3: 3210 | No cue: 0123 | No cue: 3210 |
|---|---:|---:|---:|---:|
| Fable's original dual-order News weights | 7.3% | 1.0% | 1.0% | 1.0% |
| Hand-specified ideal chain, contextual reference | 51.0% | 68.8% | 0.0% | 42.7% |
| **Learned nearest-predecessor edges, fixed taps 0+1** | **68.8%** | **80.2%** | 3.1% | 32.3% |
| Learned edges, fixed anticipatory taps 6+7 | 64.6% | 67.7% | 4.2% | 12.5% |
| Learned edges and learned 16-tap filter | 65.6% | 66.7% | 12.5% | 17.7% |
| Learned edges, randomized filter tap assignments | 3.1% | 0% | 3.1% | 0% |
| Learned edges and filter, permuted neuron labels | 2.1% | 5.2% | 0% | 5.2% |

Cue-minus-no-cue advantages for **learned edges with fixed 0+1 taps**: **+65.6 percentage points** forward (95% seed-bootstrap interval +54.2 to +77.1), **+47.9 points** backward (+32.3 to +65.6). With learned taps: +53.1 and +49.0 points. Shuffling learned tap assignments drove total beats over 300 ticks up to approximately 100, compared with approximately 35–42 for the usable routes: **idle chatter can destabilize a filter**.

**Result and limitation.** The original News rule is not the only local rule possible. A deliberately specified *nearest preceding event* rule does construct adjacency from experience and supports cue-sensitive replay. But **the learned sixteen-tap filter does not outperform fixed beat-only taps 0+1**; the major contribution is learning *who is the next neighbour*, not yet learning a better geometrical observation. Shuffled taps establish that observation choice matters, not that this particular adaptive choice is optimal. In this task the trained A and B orders come from different endpoint cues; no arbitrary context-dependent switching has been learned. The rule was tailored to the teaching gap of 3 ticks (its credit window is 1–5), and generalization to different timings and tasks remains untested. Free-running replay is still substantial in some configurations.

The next genuinely discriminating experiment, if pursued, is to train over **unseen and varied time gaps** while holding the learning rule and all thresholds fixed. Only if learned taps beat a well-chosen fixed-tap control there would we have evidence that adapting observation geometry has computational value beyond learning adjacency.

## Sixth round: checking the fifth

`experiments/round5_check.py`, numbers in `results/round5_check.json`. Sol's nearest-predecessor learner unchanged; only the spacing of the taught beats and the order of the teaching blocks vary. Fixed taps 0–1, 12 starts, 96 probes per row.

| Ticks between taught beats | Adjacent weight | Shortcut weight | Cue 0: 0123 | Cue 3: 3210 | No cue: 0123 / 3210 |
|---|---|---|---|---|---|
| 1 | 0.218 | 0.028 | 59% | 72% | 7% / 28% |
| 2 | 0.208 | 0.027 | 55% | 78% | 3% / 41% |
| 3 (round five) | 0.198 | 0.032 | 69% | 80% | 3% / 32% |
| 3, teaching ends on 0→3 instead | 0.197 | 0.032 | 78% | 68% | 31% / 5% |
| 4 | 0.188 | 0.032 | 60% | 74% | 4% / 30% |
| 5 | 0.179 | 0.033 | 66% | 72% | 8% / 24% |
| 6 | 0.027 | 0.031 | 0% | 25% | 0% / 15% |
| 8 | 0.027 | 0.029 | 0% | 17% | 0% / 13% |

- The rule builds a clean chain at every spacing inside its 1–5 tick window and learns nothing outside it. At spacings 1 and 2 the unit two back is also inside the window and the chain is still clean, so the nearest-wins competition does real work.
- The unprompted replay follows whichever order was taught last (row 4 against row 3). It is leftover timing, the fast memory of the first round, not the chain. Cue 3 "succeeds" 17–25% of the time even where nothing was learned. The cue-3 and no-cue-3210 figures in rounds four and five are inflated by about that much.
- During teaching the beats of units 0–3 are forced and the weights stay at 0.02; the rule counts which forced beat preceded which and the weights are computed afterwards. The same weights would come from the schedule with no colony running. It learns order, not timing: replay runs at the trigger's five ticks per hop whatever was taught.

**Open:** a rule in which the unit's own state takes part (as in the news rule) and which builds the chain (as the nearest-predecessor rule does).

## How close to a neuron

| A neuron has | The colony has | Standing |
|---|---|---|
| Threshold, refractory period, reset | the forgetting clock | measured, one unit |
| Synapses that follow history | `learned_weight` under the news rule | measured, one task |
| Timing-dependent writing | an input before the beat is written, one after is not | resemblance only; nothing weakens a late edge |
| Scaling that keeps a quiet cell alive | silent units shrink their incoming weights | hand-written and too weak: at 4× the learning rate the colony dies (0.5 of 6 alive) |
| Excitation and inhibition | one sign natively; a hand-written trigger was added for the third round | bolted on, not learned with |
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
- **The engineered nearest-predecessor rule does construct a bidirectional adjacency pattern from the forced teaching schedule** and supports cue-sensitive replay (round five). Round six shows it works for teaching gaps 1–5 ticks but not 6 or 8; the rule therefore does not generalize outside its hand-selected eligibility window.

**Not shown**

- A *self-generated*, state-dependent learning rule that discovers the chain: not shown. In round five, the oscillators' own phase and internal state do not determine credit; the teaching schedule alone suffices to reconstruct the learned weight matrix. No general task benefit beyond this engineered sequence-replay test has been established.
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
python experiments/cue.py                    # about 5 minutes, writes results/cue.json
python experiments/ideal_chain.py            # exact two-direction adjacency control; writes results/ideal_chain.json
python experiments/tap_learning_round5.py    # learned adjacency / tap-filter ablations; writes results/tap_learning_round5.json
python experiments/round5_check.py           # Fable's 1–8-tick gap and teaching-order controls; writes results/round5_check.json
python -m unittest discover -s tests -v      # 6 tests
node tests/parity.js                         # browser arithmetic against Python
python experiments/make_taps.py /path/to/GeometricNeuronOriginReview   # rebuilds gn/taps.json from the archived nodes
```

Details of the rules and the measures: [docs/NOTE.md](docs/NOTE.md).
