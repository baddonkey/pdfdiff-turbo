from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import Iterable

from fastapi import HTTPException, status


def ensure_relative_path(path_str: str) -> Path:
    if not path_str:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing relative path")
    posix_path = PurePosixPath(path_str)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid relative path")
    return Path(*posix_path.parts)


def write_bytes(base_dir: Path, relative_path: Path, data: bytes) -> str:
    target = base_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return str(target)


def list_relative_files(base_dir: Path) -> Iterable[str]:
    if not base_dir.exists():
        return []
    return [str(path.relative_to(base_dir)).replace(os.sep, "/") for path in base_dir.rglob("*") if path.is_file()]
