"""
Update Service — SIC
Handles GitHub API checking and automated downloading of new versions.
"""
import os
import sys
import json
import subprocess
import requests
import platform
import tempfile
import datetime
import traceback
from pathlib import Path
from typing import Optional, Tuple
from .version import VERSION, GITHUB_REPO

# Log path — Python escreve aqui, PowerShell escreve em sic_update.log.
# Ambos ficam em %TEMP% e são preservados mesmo se o update falhar.
PYTHON_LOG_PATH = os.path.join(tempfile.gettempdir(), "sic_update_python.log")


def _log(msg: str):
    """Anexa mensagem com timestamp ao log. Silencioso se falhar (disk full etc.)."""
    try:
        with open(PYTHON_LOG_PATH, "a", encoding="utf-8") as f:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _show_error_box(title: str, msg: str):
    """
    Mostra MessageBox nativa do Windows (via user32.MessageBoxW).
    Funciona em builds windowed (sem console) onde print vai para o void.
    """
    if platform.system().lower() != "windows":
        return
    try:
        import ctypes
        MB_OK = 0x00000000
        MB_ICONERROR = 0x00000010
        MB_TOPMOST = 0x00040000
        ctypes.windll.user32.MessageBoxW(0, msg, title, MB_OK | MB_ICONERROR | MB_TOPMOST)
    except Exception:
        pass


class UpdateService:
    @staticmethod
    def get_latest_release() -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (version_tag, download_url) for the latest release on GitHub.
        Example: ('v1.0.1', 'https://github.com/...')
        """
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                tag = data.get("tag_name", "")
                
                # Logic to find the correct asset for the current OS
                assets = data.get("assets", [])
                system = platform.system().lower() # 'windows', 'darwin' (mac)
                
                download_url = None
                for asset in assets:
                    name = asset.get("name", "").lower()
                    # Match platform by name prefix before checking extension,
                    # so SIC_Mac.zip is never picked on Windows and vice-versa.
                    if system == "windows" and "windows" in name and (".exe" in name or ".zip" in name):
                        download_url = asset.get("browser_download_url")
                        break
                    elif system == "darwin" and ("mac" in name or "darwin" in name or "macos" in name) and (".dmg" in name or ".zip" in name or ".app" in name):
                        download_url = asset.get("browser_download_url")
                        break
                
                return tag, download_url
        except Exception as e:
            print(f"Update check failed: {e}")
        return None, None

    @staticmethod
    def is_update_available(latest_tag: str) -> bool:
        """Compares current VERSION with remote tag."""
        if not latest_tag:
            return False
        
        # Strip 'v' prefix if exists
        v_remote = latest_tag.lstrip('v').split('.')
        v_local = VERSION.lstrip('v').split('.')
        
        try:
            for i in range(len(v_remote)):
                remote_part = int(v_remote[i])
                local_part = int(v_local[i]) if i < len(v_local) else 0
                if remote_part > local_part:
                    return True
                elif remote_part < local_part:
                    return False
        except:
            return latest_tag != VERSION
            
        return False

    @staticmethod
    def download_and_install(download_url: str):
        """
        Downloads the file, extracts it (ZIP), and prepares the bootstrap restart.
        """
        global PYTHON_LOG_PATH
        import zipfile

        # Começa um log novo para esta tentativa — apaga o anterior para não
        # confundir com corridas antigas
        try:
            if os.path.exists(PYTHON_LOG_PATH):
                os.remove(PYTHON_LOG_PATH)
        except Exception:
            pass

        _log("=" * 60)
        _log(f"download_and_install() iniciado — SIC v{VERSION}")
        _log(f"Plataforma: {platform.system()} {platform.release()}")
        _log(f"sys.executable: {sys.executable}")
        _log(f"sys.frozen: {getattr(sys, 'frozen', False)}")
        _log(f"URL: {download_url}")

        # 1. Download to temp
        temp_dir = tempfile.gettempdir()

        # Windows pode retornar o path no formato 8.3 curto (ex: MARCOS~1.RAN).
        # O PowerShell não resolve short names corretamente em todos os sistemas
        # (Windows 10/11 com short names desativados), fazendo o script PS ser
        # encontrado em path inválido e sair em <1s com exit code=0 sem executar.
        # GetLongPathNameW converte C:\Users\MARCOS~1.RAN\... → C:\Users\marcos.rangel\...
        if platform.system().lower() == "windows":
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(32768)
                if ctypes.windll.kernel32.GetLongPathNameW(temp_dir, buf, len(buf)):
                    temp_dir_long = buf.value
                    _log(f"Temp dir (short): {temp_dir}")
                    _log(f"Temp dir (long):  {temp_dir_long}")
                    temp_dir = temp_dir_long
                else:
                    _log(f"GetLongPathNameW retornou 0 — mantendo path original: {temp_dir}")
            except Exception as e:
                _log(f"GetLongPathNameW falhou (não-fatal, mantendo path original): {e}")

        # Atualiza também o PYTHON_LOG_PATH para usar o long path
        if platform.system().lower() == "windows" and "~" in PYTHON_LOG_PATH:
            PYTHON_LOG_PATH = os.path.join(temp_dir, "sic_update_python.log")

        filename = download_url.split("/")[-1]
        target_zip_path = os.path.join(temp_dir, filename)
        _log(f"Temp dir final: {temp_dir}")
        _log(f"Target zip: {target_zip_path}")

        try:
            _log("Baixando arquivo...")
            resp = requests.get(download_url, stream=True)
            _log(f"  HTTP status: {resp.status_code}")
            total_bytes = 0
            with open(target_zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_bytes += len(chunk)
            _log(f"  Download OK — {total_bytes:,} bytes gravados")

            # 2. Extract Zip (limpa a pasta antes para evitar resíduos de atualizações anteriores)
            import shutil
            extract_dir = os.path.join(temp_dir, "sic_update_extracted")
            if os.path.exists(extract_dir):
                _log(f"Limpando extract_dir anterior: {extract_dir}")
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)
            _log(f"Extract dir criado: {extract_dir}")

            _log("Extraindo ZIP...")
            if platform.system().lower() == "darwin":
                # No macOS, o módulo `zipfile` do Python NÃO preserva o bit de
                # execução (+x) nem symlinks. Isso quebra a extração do .app:
                # o binário `Contents/MacOS/SIC` fica sem permissão de execução
                # e o `open` falha silenciosamente. Usar o `unzip` do sistema,
                # que preserva permissões Unix e symlinks corretamente.
                subprocess.run(
                    ["unzip", "-o", "-q", target_zip_path, "-d", extract_dir],
                    check=True,
                )
            else:
                with zipfile.ZipFile(target_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            _log("  Extração concluída")

            # Lista arquivos extraídos para o log (útil pra debug)
            extracted_files = []
            for r, _, fs in os.walk(extract_dir):
                for fn in fs:
                    extracted_files.append(os.path.join(r, fn))
            _log(f"  Arquivos extraídos ({len(extracted_files)}):")
            for ef in extracted_files[:20]:  # limita a 20 para não poluir
                _log(f"    - {ef}")

            # Find the extracted executable/app
            is_windows = platform.system().lower() == "windows"
            new_file_path = None

            if is_windows:
                # Look for SIC.exe (break em loop interno não sai do outer,
                # então usamos flag para encerrar o os.walk assim que encontrar)
                for root, _, files in os.walk(extract_dir):
                    for name in files:
                        if name.lower().endswith(".exe"):
                            new_file_path = os.path.join(root, name)
                            break
                    if new_file_path:
                        break
            else:
                # Look for SIC.app on Mac
                for root, dirs, _ in os.walk(extract_dir):
                    for name in dirs:
                        if name.endswith(".app"):
                            new_file_path = os.path.join(root, name)
                            break

                # Segurança extra: garante +x no binário principal (caso unzip
                # não tenha preservado) e remove atributo de quarentena para
                # evitar que o Gatekeeper bloqueie o app atualizado.
                if new_file_path:
                    binary = os.path.join(new_file_path, "Contents", "MacOS", "SIC")
                    if os.path.exists(binary):
                        os.chmod(binary, 0o755)
                    subprocess.run(
                        ["xattr", "-dr", "com.apple.quarantine", new_file_path],
                        check=False,
                    )

            if not new_file_path:
                _log("ERRO: executável não encontrado no ZIP extraído.")
                _show_error_box(
                    "SIC — Erro na Atualização",
                    f"Não foi possível encontrar o executável dentro do arquivo baixado.\n\n"
                    f"Log: {PYTHON_LOG_PATH}"
                )
                return

            _log(f"Executável encontrado: {new_file_path}")
            _log(f"  Tamanho: {os.path.getsize(new_file_path):,} bytes")

            # 3. Trigger Bootstrap Update
            _log("Chamando _trigger_restart_swap()...")
            UpdateService._trigger_restart_swap(new_file_path)

        except Exception as e:
            _log(f"EXCEÇÃO em download_and_install: {e}")
            _log(traceback.format_exc())
            _show_error_box(
                "SIC — Erro na Atualização",
                f"Falha ao baixar/extrair atualização:\n\n{e}\n\nLog: {PYTHON_LOG_PATH}"
            )

    @staticmethod
    def _trigger_restart_swap(new_file_path: str):
        """Creates a batch/sh script to swap the executable and restarts in a detached state."""
        current_exe = sys.executable
        _log(f"_trigger_restart_swap() — current_exe: {current_exe}")
        if "python" in current_exe.lower():
            _log("  Rodando como script (python.exe) — auto-update abortado.")
            return

        is_windows = platform.system().lower() == "windows"

        if is_windows:
            _log(f"  is_windows=True, PID={os.getpid()}")
            _log(f"  Arquivo novo existe? {os.path.exists(new_file_path)}")
            _log(f"  Exe atual existe? {os.path.exists(current_exe)}")
            _log(f"  Exe atual gravável? {os.access(current_exe, os.W_OK)}")
            _log(f"  Dir do exe gravável? {os.access(os.path.dirname(current_exe), os.W_OK)}")
            # Abandonamos o .bat em favor de PowerShell. O .bat tinha problemas
            # com pipes (tasklist|find) quando combinado com DETACHED_PROCESS,
            # encoding de paths com acentos e parsing frágil. PowerShell resolve
            # todos esses problemas: Unicode nativo, Get-Process em vez de pipe,
            # Start-Process com detachment correto.

            # Resolve o long path do temp dir para evitar MARCOS~1.RAN
            # (short names 8.3 podem não ser reconhecidos pelo PowerShell)
            tmp = tempfile.gettempdir()
            try:
                import ctypes
                buf = ctypes.create_unicode_buffer(32768)
                if ctypes.windll.kernel32.GetLongPathNameW(tmp, buf, len(buf)):
                    tmp = buf.value
            except Exception:
                pass

            ps_path  = os.path.join(tmp, "sic_update.ps1")
            log_path = os.path.join(tmp, "sic_update.log")
            exe_dir  = os.path.dirname(current_exe)
            current_pid = os.getpid()

            _log(f"  temp_dir (PS): {tmp}")

            # Escapa apenas a aspa simples (único char especial em strings PS com aspas simples)
            def ps_escape(s):
                return s.replace("'", "''")

            ps_new_file = ps_escape(new_file_path)
            ps_current  = ps_escape(current_exe)
            ps_exe_dir  = ps_escape(exe_dir)
            ps_log      = ps_escape(log_path)

            with open(ps_path, "w", encoding="utf-8-sig") as f:
                f.write(f"""# SIC Update Script
$ErrorActionPreference = 'Continue'

# Logging manual via Add-Content — mais confiavel que Start-Transcript
# em ambientes onde o cmdlet falha silenciosamente.
$LOG = '{ps_log}'
function Log($msg) {{
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $LOG -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}}

# Primeira acao: confirma que o script chegou a ser executado.
# Se este arquivo existir, o PS rodou o script. Se nao existir, o path
# do .ps1 nao foi encontrado ou o PS foi bloqueado antes de comecar.
Log "=== SIC Update Script iniciado. PS v$($PSVersionTable.PSVersion) ==="
Log "PID origem: {current_pid}"
Log "Novo arquivo: {ps_new_file}"
Log "Destino: {ps_current}"

try {{

    # 1. Aguarda o processo original (PID {current_pid}) encerrar completamente
    $timeout = 30
    while ($timeout -gt 0) {{
        $proc = Get-Process -Id {current_pid} -ErrorAction SilentlyContinue
        if (-not $proc) {{ break }}
        Start-Sleep -Seconds 1
        $timeout--
    }}
    Log "PID {current_pid} encerrado (aguardou $(30 - $timeout)s)"

    # 2. Aguarda qualquer SIC.exe remanescente fechar (bootloader parent do PyInstaller)
    $timeout = 15
    while ($timeout -gt 0) {{
        $procs = Get-Process -Name 'SIC' -ErrorAction SilentlyContinue
        if (-not $procs) {{ break }}
        Start-Sleep -Seconds 1
        $timeout--
    }}
    Log "SIC.exe remanescente encerrado (aguardou $(15 - $timeout)s)"

    # 3. Aguarda cleanup do _MEI temp dir do PyInstaller
    Start-Sleep -Seconds 2

    # 4. Remove Mark of the Web (Zone.Identifier) do novo .exe.
    #    Arquivos baixados da internet ficam marcados como "Untrusted" e o
    #    SmartScreen/Defender pode bloquear execucao silenciosamente.
    try {{
        Unblock-File -Path '{ps_new_file}' -ErrorAction Stop
        Log "Unblock-File OK"
    }} catch {{
        Log "Unblock-File falhou (nao-fatal): $_"
    }}

    # 5. Valida que os paths existem antes de tentar mover
    if (-not (Test-Path -Path '{ps_new_file}')) {{
        throw "Novo arquivo nao existe: {ps_new_file}"
    }}
    $destDir = Split-Path -Path '{ps_current}' -Parent
    if (-not (Test-Path -Path $destDir)) {{
        throw "Diretorio de destino nao existe: $destDir"
    }}
    Log "Validacao de paths OK"

    # 6. Substitui o executavel com retry explicito
    $moved = $false
    for ($i = 1; $i -le 5; $i++) {{
        try {{
            Move-Item -Path '{ps_new_file}' -Destination '{ps_current}' -Force -ErrorAction Stop
            $moved = $true
            Log "Move-Item OK na tentativa $i"
            break
        }} catch {{
            Log "Move-Item tentativa $i falhou: $_"
            Start-Sleep -Seconds 2
        }}
    }}
    if (-not $moved) {{
        throw "Falha ao mover o executavel apos 5 tentativas. SIC.exe ainda aberto ou sem permissao de escrita."
    }}

    # 7. Aguarda Windows comprometer o arquivo no disco
    Start-Sleep -Seconds 2

    # 8. Limpa variaveis do PyInstaller — sem isso o novo SIC.exe herda
    #    _MEIPASS apontando para um _MEI antigo deletado → "failed to load python dll"
    Remove-Item Env:\\_MEIPASS -ErrorAction SilentlyContinue
    Remove-Item Env:\\_PYI_APPLICATION_HOME_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:\\PYTHONHOME -ErrorAction SilentlyContinue
    Remove-Item Env:\\PYTHONPATH -ErrorAction SilentlyContinue
    Log "Variaveis PyInstaller limpas"

    # 9. Lanca o novo SIC.exe
    Log "Chamando Start-Process..."
    Start-Process -FilePath '{ps_current}' -WorkingDirectory '{ps_exe_dir}' -ErrorAction Stop
    Log "Start-Process OK — novo SIC.exe lancado"

}} catch {{
    Log "ERRO FATAL: $_"
    Log "$($_.ScriptStackTrace)"
    # Mostra MessageBox para o usuario ver
    Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
    [System.Windows.MessageBox]::Show(
        "Falha ao atualizar o SIC:`n`n$_`n`nLog completo em:`n{ps_log}",
        "SIC — Erro na Atualizacao",
        'OK',
        'Error'
    ) | Out-Null
}}

Log "Script PS finalizado."
# (script nao se auto-deleta para inspecao em caso de falha)
""")

            _log(f"Script PS gravado em: {ps_path}")
            _log(f"  Tamanho do script: {os.path.getsize(ps_path):,} bytes")

            # Salva uma CÓPIA do script para inspeção pós-mortem.
            copy_path = os.path.join(tmp, "sic_update_copy.ps1")
            try:
                import shutil
                shutil.copy2(ps_path, copy_path)
                _log(f"  Cópia para diagnóstico: {copy_path}")
            except Exception as e:
                _log(f"  Falha ao copiar script (não-fatal): {e}")

            # Usa path absoluto do powershell.exe. Em alguns sistemas PATH
            # pode estar corrompido ou o processo pai herdou um PATH sem System32.
            system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
            ps_exe = os.path.join(system32, "WindowsPowerShell", "v1.0", "powershell.exe")
            if not os.path.exists(ps_exe):
                _log(f"  powershell.exe não encontrado em {ps_exe}, caindo para nome simples")
                ps_exe = "powershell.exe"
            else:
                _log(f"  powershell.exe: {ps_exe}")

            # Lança o PowerShell totalmente desacoplado (DETACHED_PROCESS + CREATE_NO_WINDOW).
            # -WindowStyle Hidden garante que nenhuma janela apareça.
            # -ExecutionPolicy Bypass permite rodar o script sem configuração prévia.
            DETACHED_PROCESS = 0x00000008
            try:
                proc = subprocess.Popen(
                    [
                        ps_exe,
                        "-NoProfile",
                        "-NonInteractive",
                        "-WindowStyle", "Hidden",
                        "-ExecutionPolicy", "Bypass",
                        "-File", ps_path,
                    ],
                    creationflags=DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                    close_fds=True,
                )
                _log(f"Popen OK — PowerShell PID={proc.pid}")

                # Espera 2s e checa se o PS já morreu (indica falha imediata,
                # ex: ExecutionPolicy bloqueada, script malformado, AppLocker).
                import time
                time.sleep(2)
                rc = proc.poll()
                if rc is not None and rc != 0:
                    _log(f"  ⚠️ PowerShell já saiu com exit code={rc} — algo deu errado imediatamente.")
                    _show_error_box(
                        "SIC — Erro na Atualização",
                        f"PowerShell terminou imediatamente com erro (código {rc}).\n\n"
                        f"Verifique os logs em:\n{PYTHON_LOG_PATH}\n\n"
                        f"E a cópia do script em:\n{copy_path}"
                    )
                elif rc == 0:
                    _log("  PowerShell saiu com exit code=0 (provavelmente um launcher shim) — prosseguindo.")
                else:
                    _log("  PowerShell ainda rodando após 2s — OK, deixando prosseguir")

            except Exception as e:
                _log(f"EXCEÇÃO ao lançar PowerShell: {e}")
                _log(traceback.format_exc())
                _show_error_box(
                    "SIC — Erro na Atualização",
                    f"Falha ao lançar o PowerShell:\n\n{e}\n\nLog: {PYTHON_LOG_PATH}"
                )
                return  # não chama os._exit — deixa o Qt continuar para o usuário ver o erro
        else:
            # Mac Shell Swap
            # Extract App root (e.g. going up from SIC.app/Contents/MacOS/SIC to SIC.app)
            app_root = current_exe
            while len(app_root) > 1:
                if app_root.endswith(".app"):
                    break
                app_root = os.path.dirname(app_root)
            
            if not app_root.endswith(".app"):
                app_root = current_exe # Fallback if not bundled properly
                
            script_path = os.path.join(tempfile.gettempdir(), "sic_update.sh")
            with open(script_path, "w") as f:
                f.write(f"""#!/bin/bash
# Aguarda o processo principal encerrar completamente
sleep 2

# Remove o app antigo (se existir) e move o novo para o lugar
rm -rf "{app_root}"
mv -f "{new_file_path}" "{app_root}"

# Garante permissões de execução no binário interno (caso perdido na extração)
chmod -R u+rwX "{app_root}"
chmod +x "{app_root}/Contents/MacOS/SIC" 2>/dev/null

# Remove atributo de quarentena para evitar bloqueio do Gatekeeper
xattr -dr com.apple.quarantine "{app_root}" 2>/dev/null

# Abre o app atualizado
open "{app_root}"
rm -- "$0"
""")
            os.chmod(script_path, 0o755)
            subprocess.Popen(["/bin/bash", script_path], start_new_session=True)

        # os._exit() is required here because this method runs inside a background
        # thread. sys.exit() only raises SystemExit in the calling thread, so the
        # Qt main loop keeps running and the update script waits forever.
        # os._exit() terminates the entire process immediately, allowing the
        # bootstrap script to proceed with the file swap.
        _log("Chamando os._exit(0) — processo SIC vai morrer agora. PowerShell continua.")
        os._exit(0)
