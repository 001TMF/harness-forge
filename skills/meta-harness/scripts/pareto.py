"""Deterministic floor-respecting Pareto frontier over a Meta-Harness run log.

Reuse this instead of re-implementing the frontier each search (especially in skill+/loop mode).
The convention matches the templates: quality is maximized, cost is minimized, and any candidate
whose worst-record quality (`min_quality`) is below the floor is excluded first.

Run-log format: one JSON object per line, each with at least `agent`, `quality`, `cost`, and
`min_quality`. Last row per agent wins (so re-scores override).

Usage:
    python pareto.py run_log.jsonl --floor 0.70
    python pareto.py run_log.jsonl --floor 0.70 --quality-key fidelity --cost-key chars
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def latest_per_agent(rows: list[dict]) -> list[dict]:
    """Keep the last row per agent (re-scores override earlier ones)."""
    best: dict[str, dict] = {}
    for r in rows:
        best[r["agent"]] = r
    return list(best.values())


def pareto_frontier(
    points: list[dict],
    *,
    floor: float,
    quality_key: str = "quality",
    cost_key: str = "cost",
    min_quality_key: str = "min_quality",
) -> list[dict]:
    """Floor-respecting 2D Pareto: maximize quality, minimize cost.

    A point is kept iff no other point is both >= quality and <= cost (with at least one strict).
    Points below the floor on worst-record quality are dropped before the frontier is computed.
    """
    eligible = [p for p in points if p.get(min_quality_key, p[quality_key]) >= floor]
    # Sort quality desc, then cost asc; sweep keeping strictly-improving cost.
    ranked = sorted(eligible, key=lambda p: (-p[quality_key], p[cost_key]))
    frontier, best_cost = [], float("inf")
    for p in ranked:
        if p[cost_key] <= best_cost:
            frontier.append(p)
            best_cost = p[cost_key]
    return frontier


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Floor-respecting Pareto frontier over a run log.")
    p.add_argument("run_log", type=Path)
    p.add_argument("--floor", type=float, default=0.0)
    p.add_argument("--quality-key", default="quality")
    p.add_argument("--cost-key", default="cost")
    p.add_argument("--min-quality-key", default="min_quality")
    p.add_argument("--out", type=Path, default=None, help="write frontier JSON here")
    args = p.parse_args(argv)

    points = latest_per_agent(load_jsonl(args.run_log))
    front = pareto_frontier(
        points, floor=args.floor,
        quality_key=args.quality_key, cost_key=args.cost_key,
        min_quality_key=args.min_quality_key,
    )
    front_sorted = sorted(front, key=lambda x: x[args.cost_key])
    if args.out:
        args.out.write_text(json.dumps(front_sorted, indent=2))
    print(f"frontier ({len(front_sorted)} of {len(points)} candidates, floor={args.floor}):")
    for pt in front_sorted:
        print(f"  {pt['agent']:24} quality={pt[args.quality_key]:.3f} cost={pt[args.cost_key]:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
