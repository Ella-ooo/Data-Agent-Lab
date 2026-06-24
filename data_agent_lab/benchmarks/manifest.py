"""Manifest generation helpers for external benchmark adapters."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_task_items(source: Path) -> list[dict[str, Any]]:
    if source.is_dir():
        items: list[dict[str, Any]] = []
        for path in sorted(source.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "tasks" in payload:
                items.extend(payload["tasks"])
            else:
                items.append(payload)
        for path in sorted(source.glob("*.jsonl")):
            items.extend(
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        return items

    if source.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    return payload.get("tasks", [payload])


def _coalesce(item: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in item and item[key] not in {None, ""}:
            return item[key]
    return default


def generate_infiagent_manifest(
    *,
    source: Path,
    root: Path,
    default_tags: list[str] | None = None,
    default_subset: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Normalize local closed-form CSV tasks into the adapter manifest schema.

    Supported input fields are intentionally permissive:
    - id/task_id/query_id
    - question/prompt/query
    - csv_path/data_path/file
    - expected/answer/target
    - eval_type/evaluator_type/type
    """

    tasks: list[dict[str, Any]] = []
    tags_base = default_tags or ["infiagent", "csv"]
    for idx, item in enumerate(_read_task_items(source), start=1):
        csv_path = _coalesce(item, "csv_path", "data_path", "file", "path")
        question = _coalesce(item, "question", "prompt", "query")
        expected = _coalesce(item, "expected", "answer", "target")
        if not csv_path or not question:
            raise ValueError(f"Task item {idx} missing csv_path/data_path or question")

        csv_rel = Path(str(csv_path))
        if csv_rel.is_absolute():
            try:
                csv_rel = csv_rel.resolve().relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError(f"Absolute csv_path is outside root: {csv_path}") from exc

        task_id = str(_coalesce(item, "id", "task_id", "query_id", default=f"infiagent-{idx:04d}"))
        tags = list(dict.fromkeys([*tags_base, *item.get("tags", [])]))
        subset = _coalesce(item, "subset", default=default_subset)
        task = {
            "id": task_id,
            "question": question,
            "csv_path": csv_rel.as_posix(),
            "expected": expected,
            "eval_type": _coalesce(item, "eval_type", "evaluator_type", "type", default="exact"),
            "tags": tags,
        }
        if subset:
            task["subset"] = subset
        if "tolerance" in item:
            task["tolerance"] = item["tolerance"]
        tasks.append(task)

    return {"tasks": tasks}


def write_manifest(manifest: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output
