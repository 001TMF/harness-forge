"""Campaign-memory corpus + deterministic fidelity rubric.

This is the $0, model-free inner-loop signal for the Meta-Harness search.

Why a compression/fidelity benchmark and NOT the decision eval:
``proteus_agent.eval_decisions`` scores a *frozen* campaign's decisions. A
memory/summary candidate cannot change a frozen campaign, so that score is
constant across candidates — useless as a fitness function (the "frozen-replay
defect"). What DOES vary with a candidate is (a) how many characters its
summary injects and (b) whether the summary still preserves the load-bearing
facts a future campaign must be able to recall. That is what we grade here.

The records below are a small bootstrap corpus carrying the same load-bearing
fields the production compressor (``memory.schemas.generate_summary_text``)
keeps: target, surface, strategy, outcome, quality, difficulty, transfer hints.
Swap ``load_corpus`` for real stored ``CampaignDocument`` records when the
ChromaDB memory is seeded — the rubric does not change.
"""

from __future__ import annotations

from typing import Any

Record = dict[str, Any]


def load_corpus() -> list[Record]:
    """Return the bootstrap campaign-memory corpus (model-free, offline)."""
    return [
        {
            "campaign_id": "egfr_fab_001",
            "target_name": "EGFR domain III",
            "surface_type": "flat epitope",
            "organism_class": "human",
            "strategy": "antibody Fab, CDR-H3 redesign on a stable framework",
            "arms": 3,
            "outcome": "accept",
            "candidate_count": 4,
            "quality": 0.71,
            "difficulty": "medium",
            "transfer_hints": [
                "hotspot-guided CDR-H3 beat unconstrained diffusion",
                "framework preservation kept developability high",
            ],
            "analysis": "Flat epitope rewarded longer CDR-H3 loops reaching the cleft.",
        },
        {
            "campaign_id": "kras_pep_002",
            "target_name": "KRAS G12D switch-II",
            "surface_type": "shallow pocket",
            "organism_class": "human",
            "strategy": "macrocyclic peptide into the switch-II groove",
            "arms": 2,
            "outcome": "more_seeds",
            "candidate_count": 1,
            "quality": 0.42,
            "difficulty": "hard",
            "transfer_hints": [
                "de novo binders failed; peptide grafting was the only signal",
            ],
            "analysis": "Shallow undruggable pocket; only constrained peptides held pose.",
        },
        {
            "campaign_id": "alk7_denovo_003",
            "target_name": "ALK7 ectodomain",
            "surface_type": "convex helix bundle",
            "organism_class": "human",
            "strategy": "de novo three-helix minibinder via pxdesign",
            "arms": 4,
            "outcome": "accept",
            "candidate_count": 6,
            "quality": 0.68,
            "difficulty": "medium",
            "transfer_hints": [
                "convex surfaces favour de novo minibinders over antibodies",
                "AF2-IG and Protenix-v2 agreed on the top two",
            ],
            "analysis": "Helix bundle gave a broad hydrophobic patch for minibinders.",
        },
        {
            "campaign_id": "cldn18_vhh_004",
            "target_name": "Claudin-18.2 ECL",
            "surface_type": "small extracellular loop",
            "organism_class": "human",
            "strategy": "VHH single-domain, full CDR redesign",
            "arms": 2,
            "outcome": "reject",
            "candidate_count": 0,
            "quality": 0.21,
            "difficulty": "very hard",
            "transfer_hints": [
                "tiny epitope under-constrained every arm; needs co-crystal context",
            ],
            "analysis": "ECL too small for a confident interface; all arms low ipTM.",
        },
        {
            "campaign_id": "tnfr2_fab_005",
            "target_name": "TNFR2 CRD2",
            "surface_type": "groove",
            "organism_class": "human",
            "strategy": "antibody Fab, hotspot-anchored CDR-H3 + H2",
            "arms": 3,
            "outcome": "accept",
            "candidate_count": 3,
            "quality": 0.64,
            "difficulty": "medium",
            "transfer_hints": [
                "anchoring two CDRs to the groove rim beat single-CDR designs",
            ],
            "analysis": "Groove geometry rewarded a two-CDR pincer.",
        },
        {
            "campaign_id": "spike_denovo_006",
            "target_name": "SARS-CoV-2 RBD ridge",
            "surface_type": "exposed ridge",
            "organism_class": "viral",
            "strategy": "de novo minibinder, rfantibody backup arm",
            "arms": 4,
            "outcome": "more_seeds",
            "candidate_count": 2,
            "quality": 0.55,
            "difficulty": "medium",
            "transfer_hints": [
                "ridge epitopes drift between seeds; more seeds tightened ipSAE",
            ],
            "analysis": "High seed variance on an exposed ridge; scaling seeds helped.",
        },
    ]


# The load-bearing facts a future campaign MUST be able to recall from a
# summary. Each entry: (label, extractor -> the canonical fact strings that
# count as "present" if any appears in the summary, case-insensitive).
def _required_facts(record: Record) -> dict[str, list[str]]:
    q = record["quality"]
    return {
        "target": [record["target_name"], record["target_name"].split()[0]],
        "surface": [record["surface_type"]],
        "strategy": [record["strategy"].split(",")[0]],  # the modality phrase
        "outcome": [record["outcome"]],
        "quality": [f"{q:.2f}", f"{q:.1f}", f"{q}"],
        "difficulty": [record["difficulty"]],
        "transfer": [record["transfer_hints"][0][:18]] if record["transfer_hints"] else [],
    }


def score_fidelity(summary: str, record: Record) -> float:
    """Fraction of load-bearing facts preserved in ``summary`` (0..1).

    Deterministic, case-insensitive substring match. No LLM, no network.
    """
    hay = summary.lower()
    facts = _required_facts(record)
    scorable = [k for k, v in facts.items() if v]  # skip facts with no value
    if not scorable:
        return 1.0
    hits = 0
    for key in scorable:
        if any(variant.lower() in hay for variant in facts[key]):
            hits += 1
    return hits / len(scorable)
