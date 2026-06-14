"""Candidate interface for the memory-summary search + a module loader.

A candidate is a *summary compressor*: it takes a campaign-memory record and
returns the short natural-language string that would be injected into the
policy's context on retrieval. This is the proteus analog of Meta-Harness's
``MemorySystem`` — the single, clean, swappable surface the proposer rewrites.

The interface is deliberately model-free so the inner loop costs $0. A candidate
MAY internally restructure, re-rank, or compress however it likes, but it must
not call any network/LLM (the search stays credit-free and reproducible).
"""

from __future__ import annotations

import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Any

Record = dict[str, Any]


class SummaryCompressor(ABC):
    """Compress one campaign-memory record into an injectable summary string.

    Implementations override :meth:`summarize`. Keep it pure and deterministic:
    no I/O, no LLM calls. The whole point of the search is to find a compressor
    that preserves the load-bearing facts (high fidelity) in fewer characters
    (low context cost) than the incumbent template.
    """

    @abstractmethod
    def summarize(self, record: Record) -> str:
        """Return the summary string to inject for ``record``."""
        raise NotImplementedError


def load_compressor(module_name: str) -> SummaryCompressor:
    """Import ``agents.<module_name>`` and instantiate its SummaryCompressor.

    Mirrors Meta-Harness's loader: find the single concrete subclass in the
    module and construct it with no arguments.
    """
    module = importlib.import_module(f"agents.{module_name}")
    candidates = [
        obj
        for _, obj in inspect.getmembers(module, inspect.isclass)
        if issubclass(obj, SummaryCompressor) and obj is not SummaryCompressor
    ]
    if not candidates:
        raise ValueError(f"agents.{module_name} defines no SummaryCompressor subclass")
    if len(candidates) > 1:
        raise ValueError(
            f"agents.{module_name} defines {len(candidates)} SummaryCompressor "
            "subclasses; expected exactly one"
        )
    return candidates[0]()
