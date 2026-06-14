"""Baseline: dump every field verbatim.

Maximal fidelity, maximal context cost — the top-left anchor of the frontier.
A good candidate should match its fidelity at far fewer characters.
"""

from __future__ import annotations

from candidate_base import Record, SummaryCompressor


class FullDump(SummaryCompressor):
    def summarize(self, record: Record) -> str:
        hints = "; ".join(record.get("transfer_hints", []))
        return (
            f"Campaign {record['campaign_id']}. "
            f"Target: {record['target_name']} "
            f"({record['surface_type']}, {record['organism_class']}). "
            f"Strategy: {record['strategy']}. "
            f"Arms: {record['arms']}. "
            f"Outcome: {record['outcome']}. "
            f"Candidates: {record['candidate_count']}. "
            f"Quality: {record['quality']:.2f}. "
            f"Difficulty: {record['difficulty']}. "
            f"Transfer hints: {hints}. "
            f"Analysis: {record['analysis']}"
        )
