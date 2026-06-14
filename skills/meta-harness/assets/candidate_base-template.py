"""Candidate interface template — the one clean, swappable boundary.

ADAPT: rename `Candidate`, set the method(s) to YOUR harness surface (a retriever, summarizer,
context assembler, memory system...). Keep it small (1-4 methods) and pure where possible, so two
candidates are directly comparable. The proposer rewrites the *implementation*, never the
signature.

The loader mirrors the Meta-Harness loader: it finds the single concrete subclass in a candidate
module and instantiates it with no args.
"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Any

# ADAPT: the shape of one input item your candidate operates on.
Item = dict[str, Any]


class Candidate(ABC):
    """A drop-in harness implementation.

    Keep implementations pure and deterministic: no network, no LLM calls, no hidden global
    state. The search compares candidates by running them through this boundary — anything
    non-deterministic makes the comparison noisy and the frontier unstable.
    """

    @abstractmethod
    def run(self, item: Item) -> str:  # ADAPT: signature = your harness surface
        """Transform one item (e.g. summarize a record, rank a corpus, assemble context)."""
        raise NotImplementedError


def load_candidate(module_name: str) -> Candidate:
    """Import ``agents.<module_name>`` and instantiate its single Candidate subclass."""
    module = importlib.import_module(f"agents.{module_name}")
    found = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, Candidate) and obj is not Candidate
    ]
    if len(found) != 1:
        raise ValueError(
            f"agents.{module_name} must define exactly one Candidate subclass, found {len(found)}"
        )
    return found[0]()
