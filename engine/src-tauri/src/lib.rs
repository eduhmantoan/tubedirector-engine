use serde::Serialize;
use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;
use tauri::{Manager, State};

const ORIGIN: &str = "https://tubedirector.com.br";
const PORT: u16 = 8765;

#[derive(Default)]
struct EngineState(Mutex<Option<Child>>);

impl Drop for EngineState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[derive(Serialize)]
struct EngineInfo {
    running: bool,
    healthy: bool,
    engine: String,
    model_loaded: bool,
    output_directory: String,
    details: String,
}

#[derive(Serialize)]
struct Diagnostics {
    platform: String,
    architecture: String,
    supported: bool,
    support_message: String,
    port_available: bool,
    engine_file_present: bool,
    token_file_present: bool,
    log_path: String,
    engine_path: String,
    bridge_version: String,
}

fn token_path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    Ok(app.path().home_dir().map_err(|e| e.to_string())?.join(".tubedirector-tts-token"))
}

fn read_token(app: &tauri::AppHandle) -> Result<String, String> {
    let token = std::fs::read_to_string(token_path(app)?).map_err(|_| "Inicie o motor para criar o token de conexão.".to_string())?;
    let token = token.trim().to_string();
    if token.len() < 30 { return Err("Token local inválido.".into()); }
    Ok(token)
}

fn address() -> Result<SocketAddr, String> {
    format!("127.0.0.1:{}", PORT).parse::<SocketAddr>().map_err(|e| e.to_string())
}

fn port_in_use() -> bool {
    match address() {
        Ok(addr) => TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok(),
        Err(_) => false,
    }
}

fn engine_file(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().resource_dir().map_err(|e| e.to_string())?;
    if cfg!(debug_assertions) {
        Ok(dir.join("resources/bridge.py"))
    } else {
        let name = if cfg!(target_os = "windows") { "tubedirector-tts.exe" } else { "tubedirector-tts" };
        Ok(dir.join("resources/bin").join(name))
    }
}

fn log_file(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let dir = app.path().app_log_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&dir).map_err(|e| format!("Não foi possível criar pasta de logs: {e}"))?;
    Ok(dir.join("engine-errors.log"))
}

// The bridge uses BaseHTTPRequestHandler's HTTP/1.0 and Content-Length, not chunked encoding.
fn health(app: &tauri::AppHandle) -> Result<serde_json::Value, String> {
    let token = read_token(app)?;
    let mut stream = TcpStream::connect_timeout(&address()?, Duration::from_millis(650))
        .map_err(|_| "Motor desligado".to_string())?;
    stream.set_read_timeout(Some(Duration::from_secs(2))).ok();
    stream.set_write_timeout(Some(Duration::from_secs(2))).ok();
    let req = format!("GET /health HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nOrigin: {}\r\nX-TD-Local-Token: {}\r\nConnection: close\r\n\r\n", PORT, ORIGIN, token);
    stream.write_all(req.as_bytes()).map_err(|e| e.to_string())?;
    let mut response = Vec::new();
    stream.take(65536).read_to_end(&mut response).map_err(|e| e.to_string())?;
    let text = String::from_utf8(response).map_err(|_| "Resposta do motor inválida".to_string())?;
    let (head, body) = text.split_once("\r\n\r\n").ok_or("Resposta do motor inválida")?;
    let status = head.lines().next().unwrap_or("");
    if !status.starts_with("HTTP/1.1 200 ") && !status.starts_with("HTTP/1.0 200 ") {
        return Err("Outro serviço usa a porta 8765 ou a autorização local não corresponde.".into());
    }
    let data: serde_json::Value = serde_json::from_str(body).map_err(|_| "Resposta do motor inválida")?;
    if data.get("ok").and_then(|x| x.as_bool()) != Some(true)
        || data.get("bridge_version").and_then(|x| x.as_str()).is_none() {
        return Err("Serviço incompatível na porta 8765".into());
    }
    Ok(data)
}

fn supported_platform() -> (bool, String) {
    if cfg!(target_os = "windows") {
        (cfg!(target_arch = "x86_64"), "Windows x64: Piper TTS. Para o Qwen com GPU será necessário um motor adicional.".into())
    } else if cfg!(target_os = "macos") {
        (cfg!(target_arch = "aarch64"), "macOS Apple Silicon: Qwen MLX + Piper. Mac Intel ainda não suportado.".into())
    } else {
        (false, "Esta versão distribui instaladores somente para Windows x64 e macOS Apple Silicon.".into())
    }
}

#[tauri::command]
fn engine_diagnostics(app: tauri::AppHandle) -> Diagnostics {
    let (supported, message) = supported_platform();
    Diagnostics {
        platform: std::env::consts::OS.into(),
        architecture: std::env::consts::ARCH.into(),
        supported,
        support_message: message,
        port_available: !port_in_use(),
        engine_file_present: engine_file(&app).map(|f| f.is_file()).unwrap_or(false),
        token_file_present: token_path(&app).map(|f| f.is_file()).unwrap_or(false),
        log_path: log_file(&app).map(|p| p.display().to_string()).unwrap_or_default(),
        engine_path: engine_file(&app).map(|p| p.display().to_string()).unwrap_or_default(),
        bridge_version: health(&app).ok().and_then(|v| v["bridge_version"].as_str().map(str::to_string)).unwrap_or_else(|| "—".into()),
    }
}

#[tauri::command]
fn engine_status(app: tauri::AppHandle, state: State<'_, EngineState>) -> EngineInfo {
    let mut lock = state.0.lock().unwrap_or_else(|e| e.into_inner());
    let running = match lock.as_mut() {
        Some(child) => match child.try_wait() { Ok(None) => true, _ => { *lock = None; false } },
        None => false,
    };
    drop(lock);
    match health(&app) {
        Ok(data) => EngineInfo {
            running, healthy: true,
            engine: data["engine"].as_str().unwrap_or("Motor local").to_string(),
            model_loaded: data["model_loaded"].as_bool().unwrap_or(false),
            output_directory: data["output_directory"].as_str().unwrap_or("").to_string(),
            details: if running { "Conectado ao TubeDirector".into() } else { "Serviço local detectado; este aplicativo não o controla.".into() },
        },
        Err(error) => EngineInfo {
            running, healthy: false,
            engine: if cfg!(target_os = "windows") { "Piper" } else { "Qwen MLX + Piper" }.into(),
            model_loaded: false, output_directory: "".into(), details: error,
        },
    }
}

#[tauri::command]
fn engine_token(app: tauri::AppHandle) -> Result<String, String> { read_token(&app) }

#[tauri::command]
fn engine_start(app: tauri::AppHandle, state: State<'_, EngineState>) -> Result<(), String> {
    let (supported, message) = supported_platform();
    if !supported { return Err(message); }
    if port_in_use() { return Err("A porta 8765 já está ocupada. Feche o motor anterior antes de iniciar outro.".into()); }
    let mut lock = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(child) = lock.as_mut() {
        if child.try_wait().map_err(|e| e.to_string())?.is_none() { return Err("O motor já está inicializando.".into()); }
        *lock = None;
    }
    let executable = engine_file(&app)?;
    if !executable.is_file() { return Err(format!("Motor ausente: {}. Compile o sidecar antes de distribuir.", executable.display())); }
    let mut cmd = if cfg!(debug_assertions) {
        let mut c = Command::new(if cfg!(target_os = "windows") { "python" } else { "python3" });
        c.arg(executable);
        c
    } else { Command::new(executable) };
    let log = log_file(&app)?;
    let stderr = OpenOptions::new().create(true).append(true).open(&log)
        .map_err(|e| format!("Não foi possível preparar logs: {e}"))?;
    cmd.env("TD_TTS_SITE_ORIGIN", ORIGIN)
        .env("TD_TTS_PORT", PORT.to_string())
        .env("TD_TTS_PIPER_ONLY", if cfg!(target_os = "windows") { "1" } else { "0" })
        .stdout(Stdio::null())
        .stderr(Stdio::from(stderr));
    let child = cmd.spawn().map_err(|e| format!("Falha na inicialização: {e}. Verifique o log em {}", log.display()))?;
    *lock = Some(child);
    Ok(())
}

#[tauri::command]
fn engine_stop(state: State<'_, EngineState>) -> Result<(), String> {
    let mut lock = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = lock.take() {
        match child.kill() {
            Ok(()) => {},
            Err(e) if e.kind() == std::io::ErrorKind::InvalidInput => {},
            Err(e) => return Err(format!("Falha ao encerrar o motor: {e}")),
        }
        let _ = child.wait();
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .manage(EngineState::default())
        .invoke_handler(tauri::generate_handler![engine_status, engine_token, engine_start, engine_stop, engine_diagnostics])
        .run(tauri::generate_context!())
        .expect("Erro ao iniciar TubeDirector Engine");
}
