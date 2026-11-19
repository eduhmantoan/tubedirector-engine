# TubeDirector Engine — v0.2 (prévia técnica)

Aplicativo Tauri para transformar o computador em um motor de narração conectado ao site TubeDirector.

**Estado atual:** branch de desenvolvimento; não publicar instaladores sem testar Qwen/MLX e Piper reais. A branch `main` do site não foi alterada.

## Como funciona
- Interface desktop em HTML/CSS/JS, controlador em Rust/Tauri 2.
- Bridge Python executada localmente em `127.0.0.1:8765`, protegida por token e restrição de origem.
- No Windows x64, Piper TTS com vozes brasileiras; em macOS Apple Silicon, Qwen3-TTS via MLX com fallback Piper.
- Todo pedido de geração exige ticket de assinatura válido emitido pelo TubeDirector, e o áudio sai para a pasta local `~/Music/TubeDirector-Narracoes` (localização equivalente no Windows).

## Por que a bridge está arquivada?
O conector de publicação no GitHub aceita texto UTF-8, mas não o arquivo ZIP original do usuário. Para preservar os **exatos bytes** do `bridge.py`, seu conteúdo foi incluído em `vendor/bridge.py.gz.b64`. O script de restauração verifica SHA-256 e rejeita qualquer divergência.

## Desenvolvimento

```bash
cd engine
python scripts/restore-bridge.py
python -m unittest discover -s tests -v
python -m pip install pillow
python scripts/generate-icons.py
npm install
npm run dev
```

`npm run dev` inicia somente a interface; para iniciar a bridge em modo dev é necessário Python compatível e as dependências TTS.

## Instalação nativa (apenas sistemas suportados)

```bash
python scripts/restore-bridge.py
python -m pip install pillow
python scripts/generate-icons.py
python scripts/build-sidecar.py
npm install
npm run build
```

Para builds remotos, abra **Actions → TubeDirector Engine - installers (unsigned) → Run workflow**. O workflow só é executado manualmente, para evitar gastos inesperados com minutos de macOS/Windows. Ele gera instaladores de **teste não assinados** como artefatos temporários.

## Próxima homologação
- Executar o workflow e corrigir erros de empacotamento nativo.
- Testar em Windows x64 e macOS Apple Silicon reais.
- Validar downloads de modelos de voz, geração, download/renomeação, fila, cancelamento, login e assinatura.
- Preparar assinatura de código e experiência de atualização.
- Não disponibilizar instaladores de teste ao público antes de concluir as verificações.
