#!/usr/bin/env python3
"""Recover the exact original design browser evidence without overwriting history.

This checks integrity against the already retained original manifest. It does not
authenticate an author, rerun the original checks, or establish live integration.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


REPO = Path(__file__).resolve().parents[2]
ARCHIVE_SHA256 = "6c5c77322e79d56df988a5954830353d2493c6400750f87d040e62a054f40da6"
MANIFEST_SHA256 = "599727e7a6f25b0b2baee815e28972420da89bec95bd5a2096d372af87dfa2f0"
PACKAGE_MANIFEST_SHA256 = "e54a243dc299454147ffcfc1a6b2502aff630619c75bc024c6325deca6f4354d"
PREFIX = "waypoint-roadmap-2026-10-16/"
EXPECTED = {
    "browser-results.json": (1223, "f1305f39fc1a6d2d57d90030b6fd76ddef003f0aeae0cbd4f82e31f0ec85efb0"),
    "ui-nested.png": (112735, "e84f75a7d35e8e36a489547b7058823ba4645cc53e3dbfda758d8c26036eb19b"),
    "ui-obsidian.png": (239033, "36fd486866ac08e3abd75b7ccb8455c859f51b1c54ae9ccd177a860d75cbdb02"),
    "ui-terracotta.png": (238848, "4c4b0313f06574afad512245e678640a4dc616027a995d831041eebe398489dc"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked(data: bytes, expected_sha: str, name: str, size: int | None = None) -> bytes:
    if sha(data) != expected_sha or size is not None and len(data) != size:
        raise ValueError(f"Integrity mismatch: {name}")
    return data


def validate_browser(data: bytes) -> None:
    receipt = json.loads(data)
    expected = {"check_count": 23, "fixture": "SYNTHETIC", "mode": "offline-set-content",
                "live_codex_tested": False, "browser_http_integration": "NOT_RUN_POLICY_BLOCKED"}
    if any(receipt.get(k) != v for k, v in expected.items()) or len(receipt["checks"]) != 23:
        raise ValueError("Unexpected original receipt scope")


def recover(archive: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError("Recovery requires a new destination; use verify for an existing recovery")
    checked(archive.read_bytes(), ARCHIVE_SHA256, "source archive")
    retained = checked((REPO / "waypoint/evidence/original-delivery-manifest.json").read_bytes(),
                       MANIFEST_SHA256, "retained original manifest")
    with zipfile.ZipFile(archive) as z:
        manifest = checked(z.read(PREFIX + "waypoint/MANIFEST.json"), MANIFEST_SHA256, "archive manifest")
        if manifest != retained:
            raise ValueError("Retained and archived original manifests differ")
        package_manifest = checked(z.read(PREFIX + "PACKAGE_MANIFEST.json"), PACKAGE_MANIFEST_SHA256,
                                   "package manifest")
        inner = {entry["path"]: entry for entry in json.loads(manifest)["files"]}
        outer = {entry["path"]: entry for entry in json.loads(package_manifest)["files"]}
        contents = {}
        for name, (size, digest) in EXPECTED.items():
            relative = "evidence/" + name
            for index, path in ((inner, relative), (outer, "waypoint/" + relative)):
                if index[path]["sha256"] != digest or index[path]["size_bytes"] != size:
                    raise ValueError(f"Original manifest pin differs: {relative}")
            contents[name] = checked(z.read(PREFIX + "waypoint/" + relative), digest, relative, size)
        validate_browser(contents["browser-results.json"])
    output.mkdir(parents=True, exist_ok=False)
    for name, data in {**contents, "ORIGINAL_MANIFEST.json": manifest,
                       "SOURCE_PACKAGE_MANIFEST.json": package_manifest}.items():
        with (output / name).open("xb") as f:
            f.write(data)
    report = {
        "schema": "waypoint.historical-evidence-recovery/1", "status": "VERIFIED_RECOVERY",
        "recovered_at": datetime.now(timezone.utc).isoformat(),
        "source_archive": {"basename": archive.name, "sha256": ARCHIVE_SHA256,
                           "integrity_only_not_author_authentication": True},
        "source_manifest_sha256": MANIFEST_SHA256,
        "source_package_manifest_sha256": PACKAGE_MANIFEST_SHA256,
        "recovery_worktree_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "files": [{"path": name, "size_bytes": size, "sha256": digest,
                   "source_member": PREFIX + "waypoint/evidence/" + name,
                   "original_manifest_pin_matches": True, "outer_manifest_pin_matches": True}
                  for name, (size, digest) in EXPECTED.items()],
        "scope": {"original_run_date": "2026-10-16", "checks": 23,
                  "mode": "offline-set-content", "fixture": "SYNTHETIC",
                  "live_codex_tested": False, "browser_http_integration": "NOT_RUN_POLICY_BLOCKED",
                  "new_test_run_performed": False},
        "preservation": "Existing evidence paths were not modified; later 41-check receipt remains separate history.",
    }
    with (output / "RECOVERY.json").open("x") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return verify(output)


def verify(output: Path) -> dict:
    report = json.loads((output / "RECOVERY.json").read_text())
    if report.get("source_archive", {}).get("sha256") != ARCHIVE_SHA256:
        raise ValueError("Unexpected recovery provenance")
    for name, (size, digest) in EXPECTED.items():
        checked((output / name).read_bytes(), digest, name, size)
    checked((output / "ORIGINAL_MANIFEST.json").read_bytes(), MANIFEST_SHA256, "original manifest")
    checked((output / "SOURCE_PACKAGE_MANIFEST.json").read_bytes(), PACKAGE_MANIFEST_SHA256, "package manifest")
    validate_browser((output / "browser-results.json").read_bytes())
    return {"status": "VERIFIED", "recovered_files": len(EXPECTED),
            "original_browser_checks": 23, "new_test_run_performed": False}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("recover", "verify"))
    p.add_argument("--archive", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.command == "recover" and args.archive is None:
        p.error("recover requires --archive")
    result = recover(args.archive, args.output) if args.command == "recover" else verify(args.output)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
