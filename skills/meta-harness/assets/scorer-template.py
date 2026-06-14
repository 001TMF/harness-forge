"""$0 deterministic scorer template — the inner loop.

ADAPT: load_corpus() + score_quality() are YOUR domain. The contract the outer loop depends on:
this prints/writes a quality (0..1, higher better), a cost (lower better), and a min_quality
(worst record — used for the do-no-harm floor).

THE CARDINAL RULE: score_quality must VARY WITH THE CANDIDATE for a quality reason. If a wildly
different candidate can only move `cost` and never `quality`, you have a frozen-replay scorer and
the search will degenerate to blind cost-minimization. Grade something the candidate controls
(retrieval relevance, compression fidelity, a counterfactual decision) — not a frozen output.

No LLM, no network. Deterministic. It runs k*rounds times, so keep it fast and free.

    python scorer.py --agent <candidate_module_name>
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from candidate_base import load_candidate  # ADAPT to your interface module

LOGS = Path(__file__).parent / "logs"
Item = dict[str, Any]


def load_corpus() -> list[Item]:
    """ADAPT: return the eval records/tasks. Keep a held-out test split separate (don't score it
    here during the search). Bootstrap small, upgrade to real data later."""
    raise NotImplementedError


def score_quality(output: str, item: Item) -> float:
    """ADAPT: deterministic quality of `output` for `item`, in [0, 1], higher better.

    Must vary with the candidate for a quality reason. Examples:
      - summarizer : fraction of load-bearing facts preserved (substring/field checks)
      - retriever  : recall@k of the labeled relevant set
    Avoid LLM judges here — they reintroduce cost/noise and are Goodhart-able.
    """
    raise NotImplementedError


def cost_of(output: str, item: Item) -> float:
    """ADAPT: the cost axis. Usually injected size; exact and free."""
    return float(len(output))


def evaluate(agent_name: str) -> dict:
    candidate = load_candidate(agent_name)
    corpus = load_corpus()
    qualities, costs = [], []
    for item in corpus:
        output = candidate.run(item)
        if not isinstance(output, str):
            raise TypeError(f"{agent_name}.run returned {type(output).__name__}, expected str")
        qualities.append(score_quality(output, item))
        costs.append(cost_of(output, item))
    return {
        "agent": agent_name,
        "quality": round(statistics.fmean(qualities), 4),
        "cost": round(statistics.fmean(costs), 1),
        "min_quality": round(min(qualities), 3),  # worst record -> drives the floor
        "n": len(corpus),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score one harness candidate ($0, deterministic).")
    p.add_argument("--agent", required=True, help="candidate module name under agents/")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    result = evaluate(args.agent)
    (args.out or (LOGS / f"{args.agent}.json")).parent.mkdir(parents=True, exist_ok=True)
    (args.out or (LOGS / f"{args.agent}.json")).write_text(json.dumps(result, indent=2))
    print(f"{result['agent']:24} quality={result['quality']:.3f} "
          f"cost={result['cost']:.0f} min_quality={result['min_quality']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
