from __future__ import annotations
import json
import os
import secrets
from pathlib import Path


def private_directory(path: Path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("Waypoint data directory must not be a symlink")
    os.chmod(path, 0o700)


def load_tokens(directory: Path) -> dict:
    private_directory(directory)
    path = directory / "access.json"
    if path.is_symlink():
        raise ValueError("Token file must not be a symlink")
    if path.exists():
        value = json.loads(path.read_text())
        if not all(isinstance(value.get(key), str) and len(value[key]) >= 32 for key in ("read", "write")):
            raise ValueError("Invalid local access.json; do not overwrite existing credentials")
        os.chmod(path, 0o600)
        return value
    value = {"read": secrets.token_urlsafe(36), "write": secrets.token_urlsafe(36)}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f)
    return value
