#!/usr/bin/env python3
"""Fail early rather than publishing a UI-only installer with no local speech engine."""
import platform
from pathlib import Path
root=Path(__file__).resolve().parents[1]
filename='tubedirector-tts.exe' if platform.system()=='Windows' else 'tubedirector-tts'
executable=root/'src-tauri/resources/bin'/filename
if not executable.is_file() or executable.stat().st_size < 100_000:
    raise SystemExit('Motor não empacotado. Execute python scripts/build-sidecar.py antes de compilar o instalador.')
print('Motor incluído:',executable,'(',round(executable.stat().st_size/1024/1024,2),'MB )')
