"""Optional LLM client interface (Stretch / future)."""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.0) -> str: ...


class HeuristicLLMClient:
    """Placeholder when no external LLM is configured."""

    def complete(self, prompt: str, *, system: str = "", temperature: float = 0.0) -> str:
        raise NotImplementedError(
            "No LLM configured. Core MVP uses heuristic planner/SQL generation."
        )
