"""Run directory and artifact management."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from data_agent_lab.config import RUNS_DIR


@dataclass
class RunContext:
    run_id: str
    root: Path
    revision_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, runs_dir: Path | None = None) -> RunContext:
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        root = (runs_dir or RUNS_DIR) / run_id
        for sub in (
            "input",
            "catalog",
            "plan",
            "code",
            "outputs",
            "outputs/figures",
            "validation",
            "report",
            "evaluator",
        ):
            (root / sub).mkdir(parents=True, exist_ok=True)
        return cls(run_id=run_id, root=root)

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def write_json(self, rel_path: str, payload: dict[str, Any]) -> Path:
        target = self.path(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return target

    def write_text(self, rel_path: str, content: str) -> Path:
        target = self.path(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def append_ledger(self, event: dict[str, Any]) -> None:
        ledger_path = self.path("ledger.json")
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        else:
            ledger = {"events": []}
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        ledger["events"].append(event)
        ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def finalize_meta(self, **extra: Any) -> None:
        payload = {
            "run_id": self.run_id,
            "revision_count": self.revision_count,
            **self.metadata,
            **extra,
        }
        self.write_json("meta.json", payload)
