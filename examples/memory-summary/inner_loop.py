"""Single-candidate evaluator — the $0, model-free inner loop.

Loads one SummaryCompressor, runs it over the whole corpus, and reports two
numbers: mean fidelity (load-bearing facts preserved, 0..1) and mean context
cost (characters injected per record). No LLM, no network, fully deterministic.

    python inner_loop.py --agent baseline_incumbent
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from candidate_base import load_compressor
from corpus import load_corpus, score_fidelity

LOGS = Path(__file__).parent / "logs"


def evaluate(agent_name: str) -> dict:
    """Score one candidate over the corpus. Returns a result dict."""
    compressor = load_compressor(agent_name)
    corpus = load_corpus()

    fidelities: list[float] = []
    char_costs: list[int] = []
    per_record = []
    for record in corpus:
        summary = compressor.summarize(record)
        if not isinstance(summary, str):
            raise TypeError(
                f"{agent_name}.summarize returned {type(summary).__name__}, expected str"
            )
        fid = score_fidelity(summary, record)
        fidelities.append(fid)
        char_costs.append(len(summary))
        per_record.append(
            {"campaign_id": record["campaign_id"], "fidelity": round(fid, 3),
             "chars": len(summary)}
        )

    return {
        "agent": agent_name,
        "mean_fidelity": round(statistics.fmean(fidelities), 4),
        "mean_chars": round(statistics.fmean(char_costs), 1),
        "min_fidelity": round(min(fidelities), 3),
        "n": len(corpus),
        "per_record": per_record,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score one summary compressor.")
    parser.add_argument("--agent", required=True, help="module name under agents/")
    parser.add_argument("--out", type=Path, default=None, help="write result JSON here")
    args = parser.parse_args(argv)

    result = evaluate(args.agent)
    out = args.out or (LOGS / f"{args.agent}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))

    print(
        f"{result['agent']:24}  fidelity={result['mean_fidelity']:.3f}  "
        f"chars={result['mean_chars']:.0f}  min_fid={result['min_fidelity']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
