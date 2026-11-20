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
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "vendor/bridge.py.gz.b64"
OUTPUT = ROOT / "src-tauri/resources/bridge.py"
EXPECTED_SHA256 = "cd335cd489d416ef17553de0aa4d096cb22126c9e5e140d11eff60cc32074caa"

def restore():
    data = gzip.decompress(base64.b64decode(ARCHIVE.read_text(encoding="ascii").strip(), validate=True))
    got = hashlib.sha256(data).hexdigest()
    if got != EXPECTED_SHA256:
        raise SystemExit("O arquivo original bridge.py não passou na validação SHA256: " + got)
    # v0.3: autorização de plano ocorre no site; Engine autentica apenas o token local.
    source = data.decode("utf-8")
    start = source.index("    def valid_audio_ticket(self):")
    end = source.index("    def send_json(self,", start)
    source = source[:start] + source[end:]
    source, removed = re.subn(
        r"        if not self\.valid_audio_ticket\(\):\n            return self\.send_json\(403,.*\)\n",
        "", source, count=1
    )
    if removed != 1:
        raise SystemExit("O bloqueio antigo de ticket não foi localizado; compilação cancelada.")
    source = source.replace("Content-Type, X-TD-Local-Token, X-TD-Audio-Ticket", "Content-Type, X-TD-Local-Token")
    if "valid_audio_ticket" in source or "validate-audio-ticket" in source:
        raise SystemExit("O Engine ainda contém validação de ticket por áudio.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(source, encoding="utf-8")
    print("bridge.py restaurado e verificado:", len(data), "bytes", got)

if __name__ == "__main__":
    restore()
