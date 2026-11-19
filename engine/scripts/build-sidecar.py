#!/usr/bin/env python3
"""Execute on the target OS/architecture. Bundles Piper (Windows) or Qwen MLX+Piper (Apple Silicon)."""
import platform, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if platform.system() not in ('Windows','Darwin'):
    raise SystemExit('Compilação de sidecar suportada apenas em Windows ou macOS.')
if platform.system()=='Darwin' and platform.machine()!='arm64':
    raise SystemExit('Esta primeira versão do Qwen MLX requer macOS Apple Silicon (arm64).')
packages=['pyinstaller>=6,<7','piper-tts']
if platform.system()=='Darwin': packages+=['mlx-audio','numpy']
print('Instalando dependências de build em seu ambiente Python...')
subprocess.run([sys.executable,'-m','pip','install',*packages],check=True)
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--name','tubedirector-tts','--collect-all','piper','--collect-all','onnxruntime']
if platform.system()=='Darwin':
    args += ['--collect-all','mlx_audio','--collect-all','mlx','--collect-all','numpy']
args += [str(ROOT/'src-tauri/resources/bridge.py')]
subprocess.run(args,cwd=ROOT,check=True)
executable=ROOT/'dist'/('tubedirector-tts.exe' if platform.system()=='Windows' else 'tubedirector-tts')
target=ROOT/'src-tauri/resources/bin'/executable.name
target.write_bytes(executable.read_bytes())
if platform.system()!='Windows': target.chmod(0o755)
print('Sidecar pronto:',target)
