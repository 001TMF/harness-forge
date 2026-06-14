# Worked example — optimizing proteus's campaign-memory summarizer

A complete, runnable instance of the method ships in this repo at `examples/memory-summary/`. It
searches over the **summary compressor**: the code that turns a stored campaign record into the
short string injected into the policy's context on retrieval. Use it as a reference
implementation, or copy it and replace the domain pieces for a new search. (It is drawn from a
real use case — optimizing the campaign-memory summarizer of an autonomous protein-design agent —
but the corpus is small synthetic illustrative data.)

## The framing

- **Fixed model:** the proteus policy (any swappable API model). Untouched.
- **Harness surface:** the campaign-memory summarizer (proteus's
  `memory.schemas.generate_summary_text`).
- **Why a compression search (and not the decision eval):** `proteus_agent.eval_decisions`
  scores a *frozen* campaign's decisions — a summarizer candidate can't change a frozen campaign,
  so that score is constant across candidates (the frozen-replay defect). What *does* vary is how
  many characters a candidate injects and whether it preserves the load-bearing facts. So the
  objective is: **minimize chars subject to fidelity ≥ floor.** This is the exact shape of the
  Meta-Harness paper's headline result (more accuracy at far fewer tokens).
- **Two Pareto axes:** quality = fidelity (fraction of load-bearing facts preserved, 0..1);
  cost = injected characters. Floor = 0.70 worst-record fidelity (do-no-harm).

## The files (the five blocks, instantiated)

| File | Block | Role |
|---|---|---|
| `candidate_base.py` | candidate interface | `SummaryCompressor` ABC + `load_compressor()` |
| `corpus.py` | corpus + rubric | 6 campaign records + `score_fidelity()` (the $0, deterministic rubric) |
| `inner_loop.py` | scorer | runs a candidate over the corpus → `{mean_fidelity, mean_chars, min_fidelity}` |
| `agents/baseline_incumbent.py` | baseline | port of `generate_summary_text` — the system to beat (269 chars @ 1.0 fidelity) |
| `agents/baseline_full.py` | baseline | dump-everything anchor (369 chars @ 1.0 fidelity) |
| `.claude/skills/meta-harness-proteus/SKILL.md` | proposer prior | steers proposers toward mechanism-level compression |
| `config.yaml` | config | floor, proposer model, cost model notes |
| `native_meta_harness_workflow.js` | the native loop | the `Workflow` script that runs the whole search |
| `score_baselines.py` | demo runner | scores the baselines + prints the frontier, $0, no model |

The native workflow is the entire "outer loop" — it replaces the Stanford repo's
`claude_wrapper.py` + `meta_harness.py` (which this repo deliberately does **not** vendor).

## Run it natively ($0 inner loop)

Score the baselines + form the frontier with no model, no network:

```bash
cd examples/memory-summary
python score_baselines.py                         # baselines + frontier, $0
# or score a single candidate directly:
python inner_loop.py --agent baseline_incumbent   # -> fidelity=1.000 chars=269
```

Run the actual search via the native Workflow (the recommended mode) — invoke the `Workflow` tool
with the absolute path to the example dir:

```
Workflow({ scriptPath: "<abs>/examples/memory-summary/native_meta_harness_workflow.js",
           args: { dir: "<abs>/examples/memory-summary", rounds: 2, k: 3 } })
```

This fans out `k` proposer agents per round (each writes one compressor into `agents/`), scores
each via the $0 `inner_loop.py`, and Pareto-merges. The proposer agents run on the session model;
the scorer is free. The frontier starts at the 269-char incumbent — a successful round produces a
compressor that holds fidelity ≥ floor at < 269 chars.

## What "success" looks like

A frontier point that strictly dominates the incumbent: same-or-higher fidelity at fewer
characters. The *frontier* (the fidelity/chars tradeoff curve), not a single winner, is the
deliverable. Before any winner is adopted into proteus, re-validate it on real stored
`CampaignDocument`s with an antigen-family-disjoint split (the entrenchment firewall) — the
bootstrap corpus in `corpus.py` is a pilot, not a validated benchmark.

## Adapting to a new domain

1. Replace `corpus.py` — your records + your deterministic rubric (the part that must *vary with
   the candidate*).
2. Replace `candidate_base.py` — your swappable interface.
3. Rewrite the proposer prior for your domain's mechanisms + anti-leakage rules.
4. Point `native_meta_harness_workflow.js` at the new dir; adjust `k`, rounds, floor.

Everything else — the loop, the Pareto math, the proposer/scorer orchestration — is unchanged.
