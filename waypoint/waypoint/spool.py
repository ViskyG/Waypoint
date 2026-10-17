"""Bounded local outbox for observation events only, never for plan mutations."""
from __future__ import annotations
import json
import os
import uuid
import time
from pathlib import Path
from .domain import ContractError, canonical, validate_event
from .security import private_directory

MAX_FILES = 1000
MAX_BYTES = 32 * 1024 * 1024


def queue(directory: Path, events: list[dict]) -> str:
    values = [validate_event(e) for e in events]
    path = directory / "outbox"
    private_directory(path)
    import fcntl
    with (path / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        files = list(path.glob("*.json"))
        body = canonical({"events": values}).encode()
        if len(files) >= MAX_FILES or sum(p.stat().st_size for p in files if not p.is_symlink()) + len(body) > MAX_BYTES:
            raise ContractError("outbox_full", "Observation outbox is full; signal not recorded")
        receipt = uuid.uuid4().hex
        name = f"{time.time_ns():020d}-{receipt}"
        temporary = path / (name + ".tmp")
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(body); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path / (name + ".json"))
        directory_fd = os.open(path, os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return receipt


def drain(directory: Path, store) -> dict:
    path = directory / "outbox"
    if not path.exists():
        return {"accepted": 0, "rejected": 0}
    accepted = rejected = 0
    for file in sorted(path.glob("*.json"))[:100]:
        if file.is_symlink() or file.stat().st_size > 8_000_000:
            continue
        try:
            batch = json.loads(file.read_text())
            store.ingest(batch["events"])
            file.unlink()
            accepted += 1
        except (ValueError, KeyError, ContractError):
            target = directory / "rejected-outbox"
            private_directory(target)
            os.replace(file, target / file.name)
            rejected += 1
    return {"accepted": accepted, "rejected": rejected}
