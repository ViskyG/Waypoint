#!/usr/bin/env python3
"""Verify the unpacked, unmodified delivery against its file manifest (no network)."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def verify(root: Path) -> dict:
    root = root.resolve()
    manifest = json.loads((root / 'MANIFEST.json').read_text(encoding='utf-8'))
    errors = []
    seen = set()
    for item in manifest['files']:
        relative = item['path']
        path = (root / relative).resolve()
        if relative in seen or not path.is_relative_to(root) or path == root:
            errors.append(f'invalid/duplicate manifest path: {relative}')
            continue
        seen.add(relative)
        if not path.is_file():
            errors.append(f'missing file: {relative}')
            continue
        data = path.read_bytes()
        if len(data) != item['size_bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            errors.append(f'content differs: {relative}')
        if path.suffix == '.json':
            try:
                json.loads(data)
            except (ValueError, UnicodeDecodeError):
                errors.append(f'invalid JSON: {relative}')
        if path.suffix == '.zip':
            try:
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        errors.append(f'nested archive CRC failed: {relative}')
            except zipfile.BadZipFile:
                errors.append(f'invalid nested ZIP: {relative}')
    return {'status': 'FAIL' if errors else 'PASS', 'files_checked': len(seen), 'errors': errors,
            'scope': 'file integrity of this unmodified delivery, not runtime behavior or authenticity of its author'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = verify(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {'status': 'FAIL', 'error': str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
