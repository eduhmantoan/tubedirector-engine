const { invoke } = window.__TAURI__.core;
const $=id=>document.getElementById(id);
let busy=false;
function notice(message, error=false){$('notice').textContent=message;$('notice').classList.toggle('error',error);}
async function refresh(){
  try{
    const s=await invoke('engine_status');
    $('statusPill').className='pill '+(s.healthy?'online':s.running?'':'offline');
    $('statusPill').textContent=s.healthy?'● Conectado':s.running?'◌ Inicializando':'● Desligado';
    $('engineName').textContent=s.engine;
    $('engineStatus').textContent=s.details;
    $('modelStatus').textContent=s.healthy?(s.model_loaded?'Modelo Qwen carregado. Modelos de voz disponíveis no site.':'Motor pronto. Vozes/modelos são carregados na primeira narração.'):'Inicie o motor para preparar o processamento no computador.';
    $('outputDir').textContent=s.output_directory||'Música / TubeDirector-Narracoes';
    $('start').disabled=busy||s.running||s.healthy;
    $('stop').disabled=busy||!s.running;
    if(s.healthy){try{$('token').value=await invoke('engine_token');}catch{$('token').value='Token indisponível';}}
  }catch(e){notice('Falha ao consultar o aplicativo: '+e,true);}
}
async function diagnostics(){
  try {
    const d=await invoke('engine_diagnostics');
    $('compatibility').textContent=d.support_message;
    $('diagSystem').textContent=d.platform+' / '+d.architecture+(d.supported?' ✓':' ⚠');
    $('diagBinary').textContent=d.engine_file_present?'Disponível ✓':'Ausente ⚠';
    $('diagPort').textContent=d.port_available?'Livre':'Em uso';
    $('diagBridge').textContent=d.bridge_version;
    $('logPath').textContent='Registro de erros: '+(d.log_path||'indisponível');
    if(!d.supported){$('start').disabled=true;}
  }catch(e){$('compatibility').textContent='Falha no diagnóstico: '+e;}
}
$('diagnose').addEventListener('click',diagnostics);
$('start').addEventListener('click',async()=>{busy=true;$('start').disabled=true;notice('Iniciando motor...');try{await invoke('engine_start');notice('Motor iniciado. Conecte o token no site.');}catch(e){notice(String(e),true);}finally{busy=false;await refresh();}});
$('stop').addEventListener('click',async()=>{busy=true;try{await invoke('engine_stop');notice('Motor encerrado.');$('token').value='Inicie o motor para criar o token';}catch(e){notice(String(e),true);}finally{busy=false;await refresh();}});
$('copy').addEventListener('click',async()=>{try{const t=await invoke('engine_token');await navigator.clipboard.writeText(t);notice('Token copiado. Cole na área de conexão da Narração IA.');}catch(e){notice('Não foi possível copiar o token: '+e,true);}});
$('reveal').addEventListener('click',()=>{$('token').type=$('token').type==='password'?'text':'password';});
await refresh();await diagnostics();setInterval(refresh,2400);
