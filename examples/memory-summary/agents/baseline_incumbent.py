"""Baseline: mirror the production compressor.

Faithful port of ``proteus_agent.memory.schemas.generate_summary_text`` — the
incumbent the search must beat. Covers target, strategy, arms, outcome,
candidates, quality, transfer (first 2 hints), difficulty.
"""

from __future__ import annotations

from candidate_base import Record, SummaryCompressor


class Incumbent(SummaryCompressor):
    def summarize(self, record: Record) -> str:
        transfer = record.get("transfer_hints", [])[:2]
        transfer_text = "; ".join(transfer) if transfer else "N/A"
        return (
            f"Target: {record['target_name']} "
            f"({record['surface_type']}, {record['organism_class']}). "
            f"Strategy: {record['strategy']}. Arms: {record['arms']}. "
            f"Outcome: {record['outcome']}. Candidates: {record['candidate_count']}. "
            f"Quality: {record['quality']:.2f}. Transfer: {transfer_text}. "
            f"Difficulty: {record['difficulty']}."
        )
