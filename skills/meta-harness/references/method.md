# Meta-Harness — method, fit, and guardrails

Deep reference for framing a new search. Read this when deciding *whether* a problem fits and
*how* to set up the objective. The SKILL.md body is the operational summary; this is the why.

## Table of contents

1. Harness vs. model — what is actually being optimized
2. Fit criteria (when this works, when it doesn't)
3. Choosing the objective (the two Pareto axes)
4. The frozen-replay defect — the central trap, in full
5. Guardrails (held-out, anti-Goodhart, anti-leakage, proxy-fidelity, entrenchment)
6. Relationship to RL / fine-tuning

---

## 1. Harness vs. model

A deployed LLM system has two separable parts:

- **The model** — fixed weights. Changing it means fine-tuning / RL / a bigger model.
- **The harness** — everything else: the system prompt, the memory store, the retrieval policy,
  how observations get compressed, how context is assembled and budgeted, tool-selection logic,
  planning scaffolds, summarizers. This is *code*, and it decides what information the fixed
  model sees at each step.

Meta-Harness is the claim that, for many tasks, **a large fraction of achievable gain lives in
the harness**, and that you can search over harness code automatically: an LLM proposer writes
candidate harnesses, a cheap evaluator scores them, and you keep the Pareto-best. The model
never changes — which is exactly why it fits a fixed/off-the-shelf-API deployment, where you
*can't* change the weights.

The paper's headline text-classification result: an evolved memory system reached **+7.7
accuracy points at ~4× fewer context tokens** than the hand-written baseline — a pure
harness-side win at fixed model.

## 2. Fit criteria

Strong fit when several hold:

| Property | Why it matters |
|---|---|
| Base model is **fixed** | The premise. Gain must come from the harness, not weights. |
| **Repeated** episodes / tasks | A harness change has to pay off across many runs, not one. |
| A **measurable eval with a real metric** | The search needs a fitness signal it can trust. |
| Eval is **cheap enough to run many times** | You score `k × rounds` candidates; per-eval cost dominates feasibility. |
| Search set **large enough** to expose failures, **small enough** to iterate | Too few tasks → the frontier overfits; too many → each round is slow. |
| **Recurring error patterns** a harness could fix | E.g. context bloat, poor retrieval, lost-in-the-middle. |
| **Offline traces / prior runs** exist | Warm-starts the proposer and seeds the eval. |
| A plausible **held-out test** | So a frontier win is real, not memorized. |

**Poor fit / stop:** the gain must come from the base model; or there is no stable evaluation
loop (purely subjective "feels smarter"); or you cannot construct an eval that *varies with the
candidate* (see §4) — in that case you would only be optimizing cost, blind to quality.

## 3. Choosing the objective (the two Pareto axes)

Meta-Harness is multi-objective. Pick:

- **Axis 1 — quality.** The real success signal. Prefer a deterministic, $0 proxy for the inner
  loop (it runs hundreds of times); reserve the expensive/true metric for a final audit. Examples:
  classification accuracy; retrieval recall@k against a labeled relevant set; compression
  fidelity (load-bearing facts preserved); task-completion rate.
- **Axis 2 — cost.** Almost always **injected context size** (chars/tokens), measured exactly
  and for free. Sometimes latency, $ spend, or tool-call count.

The frontier is the set of candidates where no other is both higher-quality and lower-cost. The
*product* is the whole curve, not a single point — it tells you the achievable quality at each
cost budget.

**The safest first objective** is almost always **"minimize cost subject to quality ≥ a
do-no-harm floor"** rather than "maximize quality." Maximizing a soft quality proxy invites
Goodharting (§5); minimizing cost under a floor is robust and still captures most of the value
(the +7.7pts/4×-fewer-tokens result is a cost-minimization-at-fixed-quality story).

## 4. The frozen-replay defect — in full

This is the single most common way a harness search produces a confident, meaningless result.
Internalize it.

**Setup.** To make the inner loop cheap, you are tempted to evaluate candidates by *replaying
cached runs* — a recorded trace, a stored campaign, a logged conversation — instead of executing
the system live.

**The defect.** In a cached trace, the outputs are **frozen**. The retrieval that happened, the
context that was shown, the model's decisions, and the final scored result are all baked into the
recording. A scaffolding candidate (a new retrieval ranker, a new summarizer, a new context
assembler) **cannot change any of those frozen outputs**. So when you score the replayed trace:

- The **quality** axis is constant across candidates — it reflects the *old* harness that
  produced the recording, not the candidate.
- The only thing that genuinely moves is the **cost** axis (how many chars the candidate *would*
  inject).

A naive Pareto search "maximize quality, minimize cost" therefore drives cost to the floor (drop
summaries, retrieve nothing, empty the assembler) while quality never drops — because the proxy
is structurally blind to quality. You get a frontier that looks like a triumph and means nothing.

**How to know you're in this trap:** ask "if I swap in a wildly different candidate, can this
eval number actually change for a quality reason?" If the answer is "only the cost number
changes," you are replaying frozen outputs.

**Fixes (any of):**

1. **Grade a quantity that genuinely varies with the candidate.** For a memory/retrieval/summary
   search this is: retrieval relevance against a labeled or proxy ground truth; or compression
   *fidelity* — does the candidate's summary still contain the load-bearing facts? (This is what
   the proteus example does — fidelity moves with the candidate; an over-aggressive compressor
   loses facts and loses fidelity.)
2. **Counterfactual decision-replay** instead of output-replay: hold the task sequence fixed but
   *re-run* the candidate's retrieval/summarization at each decision point and measure whether the
   *evaluated decision* would change. Heavier than pure replay, but honest.
3. **Quality as a one-sided floor.** Use the (possibly frozen) quality metric only as a
   do-no-harm regression guard, and optimize cost. Then "blindness to quality improvements" is
   acceptable because you are not claiming any — you are claiming a lossless cost reduction.
4. **Live execution** for the inner loop — only viable if a live run is cheap enough.

## 5. Guardrails

- **Held-out discipline.** The proposer sees the search-set results and the frontier — never the
  test split. The test split is scored exactly once, at the very end. Physically separate the
  test outputs from the search logs so a proposer agent cannot read them.
- **Anti-Goodhart floor.** The proposer (a strong code-writing agent with read access to the
  scorer) will find and exploit any soft spot in the metric — including known reward bugs and
  "returns success when data is missing" paths. Put a **hard quality floor** on the frontier and
  **fix known scorer bugs before** running, or the search optimizes the bug.
- **Anti-leakage.** Forbid candidates from hardcoding any value, id, or name from the eval set.
  Candidates must generalize. State this in the proposer prior and, ideally, check for it.
- **Proxy-fidelity gate.** If the inner loop is a cheap proxy for an expensive true metric,
  *validate the proxy before trusting it*: take the incumbent plus a few deliberately-degraded
  variants, score them on both the proxy and the true metric, and require the rankings to agree
  (e.g. Spearman ≥ ~0.7) before spending proposer budget. If an emptied-context candidate wins on
  the proxy but loses on the true metric, the proxy is disqualified.
- **Entrenchment firewall.** A frontier winner is a *proposal*, not a commit. A search that ran
  against a leaky/tiny/proxy eval can produce scaffolding that looks great in-loop and is wrong
  live. Never auto-promote: re-validate on the untouched test split (and, for proxy searches, on
  the live metric) on a slice disjoint from anything the search saw, before it becomes the
  incumbent.

## 6. Relationship to RL / fine-tuning

Meta-Harness and RL are **complementary, not competing** — they optimize different objects:

- **RL / fine-tuning** changes the **model weights**. Needs a trainable model + training
  infra/GPU. Unavailable when the model is a fixed off-the-shelf API.
- **Meta-Harness** changes the **harness code** around a fixed model. Runs on CPU + a proposer
  agent; no trainable model.

In a fixed-base-model phase, Meta-Harness is the *only* available optimizer, and it is the
natural **first** one: it forces you to harden the eval/reward (fix scorer bugs, build a clean
held-out split) at low cost — exactly the groundwork a later RL phase also depends on. A
Meta-Harness-tuned harness then becomes a better, leaner starting point for RL (cleaner context →
cheaper rollouts, clearer credit assignment).
