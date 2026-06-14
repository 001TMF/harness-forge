"""Score the baselines and print the floor-respecting Pareto frontier — $0, no model.

This is the demo "outer loop" with the proposer removed: it just evaluates the two shipped
baselines and shows the frontier they form. The real search (with proposers writing new
candidates) is the native Workflow in native_meta_harness_workflow.js.

    python score_baselines.py
"""

from __future__ import annotations

from inner_loop import evaluate

FLOOR = 0.70
BASELINES = ["baseline_full", "baseline_incumbent"]


def pareto(points: list[dict]) -> list[dict]:
    """Floor-respecting 2D Pareto: maximize fidelity, minimize chars."""
    eligible = [p for p in points if p["min_fidelity"] >= FLOOR]
    ranked = sorted(eligible, key=lambda p: (-p["mean_fidelity"], p["mean_chars"]))
    out, best = [], float("inf")
    for p in ranked:
        if p["mean_chars"] <= best:
            out.append(p)
            best = p["mean_chars"]
    return out


def main() -> int:
    scored = [evaluate(name) for name in BASELINES]
    for s in scored:
        print(f"  {s['agent']:22} fidelity={s['mean_fidelity']:.3f} chars={s['mean_chars']:.0f}")
    print(f"\nPareto frontier (fidelity >= {FLOOR}):")
    for p in sorted(pareto(scored), key=lambda x: x["mean_chars"]):
        print(f"  {p['agent']:22} fidelity={p['mean_fidelity']:.3f} chars={p['mean_chars']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
