#!/usr/bin/env python3
"""Restore exact original TubeDirector voice bridge; checksum protects source integrity.

The archive is base64 text because our GitHub connector only supports UTF-8 file writes.
Restore locally or in CI; the generated bridge.py is deliberately not checked into this branch.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "vendor/bridge.py.gz.b64"
OUTPUT = ROOT / "src-tauri/resources/bridge.py"
EXPECTED_SHA256 = "cd335cd489d416ef17553de0aa4d096cb22126c9e5e140d11eff60cc32074caa"

def restore():
    data = gzip.decompress(base64.b64decode(ARCHIVE.read_text(encoding="ascii").strip(), validate=True))
    got = hashlib.sha256(data).hexdigest()
    if got != EXPECTED_SHA256:
        raise SystemExit("O arquivo original bridge.py não passou na validação SHA256: " + got)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(data)
    print("bridge.py restaurado e verificado:", len(data), "bytes", got)

if __name__ == "__main__":
    restore()
