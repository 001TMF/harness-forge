# Building blocks — the five pieces you supply

The native loop handles orchestration. These five are the domain logic *you* build. Templates
live in `assets/`; this file explains how to build each one well.

## 1. The candidate interface

A candidate is a drop-in implementation of one **clean, swappable boundary**. The whole search
depends on this boundary existing: if your harness logic is tangled inside one big function,
extract the boundary first, or there is nothing to swap.

A good interface is:

- **Small** — one ABC/Protocol with 1–4 methods. The proposer rewrites the *implementation*, not
  the signature.
- **Pure where possible** — deterministic, no hidden global state, so two candidates are
  comparable.
- **The actual lever** — it must be the thing whose variation moves the metric. (Optimizing a
  boundary that doesn't affect quality or cost is wasted search.)

Template: `assets/candidate_base-template.py` — an ABC plus a `load(module_name)` that finds the
single subclass in a candidate file and instantiates it (mirrors the Meta-Harness loader).

Examples of good boundaries: a retrieval ranker (`rank(query, corpus) -> ordered ids`); a
summarizer (`summarize(record) -> str`); a context assembler (`assemble(observations) -> str`);
a memory system (`predict` / `learn_from_batch` / `get_state`).

## 2. The $0 deterministic scorer + rubric

The inner loop. It runs `k × rounds` times, so it must be **cheap (no LLM, no network)**,
**deterministic** (same candidate → same score, so the frontier is stable), and — most
importantly — it must **vary with the candidate**.

> **The cardinal rule:** before writing the scorer, ask "if I swap in a wildly different
> candidate, can this number change for a *quality* reason?" If only the cost number can move,
> you are about to build a frozen-replay scorer that the search will game by minimizing cost
> blindly. See `references/method.md` §4. Fix it by grading something the candidate actually
> controls: retrieval relevance, compression fidelity, or a counterfactual decision.

Structure (template: `assets/scorer-template.py`):

- Load the candidate via the interface loader.
- Run it over the eval corpus.
- Compute **two numbers**: a quality score (0..1, higher better) and a cost (lower better).
- Also compute a **worst-case** quality (e.g. `min` over the corpus) — the frontier uses this for
  the do-no-harm floor, so one catastrophic record can't be hidden by a good average.
- Write a small result JSON; print a one-line summary.

**The rubric** is the heart of the quality score. Make it check the things that *must* survive a
good candidate. For a summarizer: the fraction of load-bearing facts still present (substring /
field checks). For a retriever: recall@k against a labeled (or proxy) relevant set. Keep it
deterministic — substring/field/set logic, not an LLM judge (an LLM judge reintroduces cost and
noise, and can be Goodharted).

## 3. The eval corpus + held-out split

The tasks/records candidates are graded on. Requirements:

- **Big enough to expose failure modes, small enough to iterate.** A handful is fine to start;
  more is better for trustworthy ranking. If you have very few, be honest that the frontier is
  provisional.
- **A held-out test split** that shares no leaky structure with the search set. "Leaky structure"
  is domain-specific: the same template, the same customer, the same antigen family, the same
  source document. Split so the test set is genuinely novel — otherwise a frontier "win" is
  memorization.
- **Bootstrap, then upgrade.** It is fine to start with a small hand-built or synthesized corpus
  to get the loop running, then swap in real data later. Mark the bootstrap clearly so nobody
  mistakes a pilot frontier for a validated result.

## 4. The proposer prior

A short mini-SKILL the proposer agents read each round. Its job is to make proposals *good*:

- **Mechanism-level changes, not constant-tuning.** The most common failure mode is candidates
  that are the baseline with a number changed — these almost always tie or regress. Push for new
  *mechanisms*: a different algorithm, encoding, structure, or strategy. (Template lists concrete
  axes.)
- **Anti-leakage.** Forbid hardcoding any eval-set value; candidates must generalize.
- **Mandatory quick prototype + self-critique.** Have the proposer sanity-check its idea on a
  couple of records before committing, and re-read its candidate asking "is this a real mechanism
  or a tweaked constant?"
- **Exactly k candidates, no early abort.** Don't let the proposer declare the frontier optimal.

Template: `assets/proposer-prior-template.md`. In Workflow mode, tell each proposer agent to read
it; in `/loop` mode, fold it into the loop skill body.

## 5. The frontier + run log (state)

Two artifacts:

- **Run log** — append-only, one row per scored candidate: `{iteration, agent, quality, cost,
  min_quality, passes_floor, hypothesis}`. This is the proposer's "gradient" — it reads what was
  tried and how it did.
- **Frontier** — the floor-respecting 2D Pareto set over all scored candidates: maximize quality,
  minimize cost, keep only points where no other is both higher-quality and lower-cost, after
  dropping any below the quality floor.

`scripts/pareto.py` computes the frontier from a run-log JSONL deterministically — reuse it
rather than re-implementing Pareto each time. In Workflow mode the frontier also lives in a JS
variable across rounds; persist it to disk for resume / inspection.

## Putting it together

A complete, runnable instance of all five — for optimizing proteus's campaign-memory summarizer —
is at `~/mh-proteus/` and walked through in `references/proteus-example.md`. When starting a new
domain, copying that scaffold and replacing `corpus.py` (records + rubric) + the candidate
interface is usually faster than starting from the bare templates.
