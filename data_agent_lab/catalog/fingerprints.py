"""Dataset fingerprinting for cache invalidation."""

from __future__ import annotations

import hashlib
from pathlib import Path


def fingerprint_paths(paths: list[Path]) -> str:
    hasher = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p)):
        hasher.update(str(path.resolve()).encode())
        if path.is_file():
            stat = path.stat()
            hasher.update(str(stat.st_size).encode())
            hasher.update(str(int(stat.st_mtime)).encode())
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    stat = child.stat()
                    hasher.update(str(child.relative_to(path)).encode())
                    hasher.update(str(stat.st_size).encode())
                    hasher.update(str(int(stat.st_mtime)).encode())
    return hasher.hexdigest()[:16]
