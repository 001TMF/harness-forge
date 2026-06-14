# Example — memory-summary search

A complete, runnable instance of the Harness Forge method. It optimizes a **summary compressor**:
the code that turns a stored record into the short string injected into a model's context on
retrieval. The objective is the canonical Meta-Harness shape — **keep the load-bearing facts in
fewer characters** (minimize chars subject to fidelity ≥ floor).

It is drawn from a real use case (the campaign-memory summarizer of an autonomous protein-design
agent), but the corpus here is small synthetic illustrative data — a pilot, not a benchmark.

## The five blocks (everything the method needs)

| File | Block |
|---|---|
| `candidate_base.py` | the swappable interface (`SummaryCompressor` + loader) |
| `corpus.py` | the records **+ the deterministic fidelity rubric** (the $0 signal) |
| `inner_loop.py` | the scorer — runs a candidate over the corpus → fidelity + chars |
| `agents/baseline_incumbent.py` | the system to beat (269 chars @ 1.0 fidelity) |
| `agents/baseline_full.py` | dump-everything anchor (369 chars @ 1.0 fidelity) |
| `.claude/skills/meta-harness-proteus/SKILL.md` | the proposer prior |
| `native_meta_harness_workflow.js` | the native outer loop (the `Workflow` script) |

## Run the $0 part (no model, no network)

```bash
cd examples/memory-summary
python score_baselines.py                        # baselines + frontier
python inner_loop.py --agent baseline_incumbent  # score one candidate
```

Expected:

```
  baseline_full          fidelity=1.000 chars=369
  baseline_incumbent     fidelity=1.000 chars=269

Pareto frontier (fidelity >= 0.7):
  baseline_incumbent     fidelity=1.000 chars=269
```

## Run the real search (native, proposer = your Claude subscription)

Invoke the `Workflow` tool with the **absolute** path to this directory:

```
Workflow({ scriptPath: "<abs>/examples/memory-summary/native_meta_harness_workflow.js",
           args: { dir: "<abs>/examples/memory-summary", rounds: 2, k: 3 } })
```

Each round fans out `k` proposer agents (each writes one compressor into `agents/`), scores each
via the $0 `inner_loop.py`, and Pareto-merges. Proposers run on your Claude subscription; the
scorer is free; there is no solver model. A successful round produces a compressor that holds
fidelity ≥ floor at **< 269 chars**.

## Make it your own

Replace `corpus.py` (your records + your rubric — the part that must *vary with the candidate*),
swap `candidate_base.py` for your interface, and rewrite the proposer prior. The loop, the Pareto
math, and the orchestration are unchanged.
