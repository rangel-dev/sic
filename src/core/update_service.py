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
from .version import VERSION, GITHUB_REPO, APP_NAME

# Log path — Python escreve aqui, PowerShell escreve em sic_update_ps.log.
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


def _ca_bundle() -> Optional[str]:
    """
    Retorna o caminho do bundle de CAs confiável. Preferimos o certifi
    (empacotado no PyInstaller via sic.spec). Se indisponível, devolve None
    e deixamos o requests cair no padrão do sistema.
    """
    try:
        import certifi
        path = certifi.where()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass
    return None


def _http_get(url: str, **kwargs) -> requests.Response:
    """
    GET com validação TLS robusta. Se a validação com certifi falhar
    (comum em redes corporativas que interpõem proxy/CA própria via GPO),
    re-tenta uma vez usando o store nativo do Windows via `truststore`,
    que é o caminho oficial e seguro para esses ambientes.
    """
    ca = _ca_bundle()
    if ca:
        kwargs.setdefault("verify", ca)
    kwargs.setdefault("timeout", 30)
    try:
        return requests.get(url, **kwargs)
    except requests.exceptions.SSLError as ssl_err:
        _log(f"SSL falhou com certifi ({ssl_err}). Tentando truststore (Windows CA store)...")
        try:
            import ssl
            import truststore
            ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            # Remove verify=<path> e força uso do contexto nativo via session adapter.
            kwargs.pop("verify", None)
            session = requests.Session()
            adapter = _TruststoreAdapter(ctx)
            session.mount("https://", adapter)
            return session.get(url, **kwargs)
        except Exception as retry_err:
            _log(f"Retry com truststore também falhou: {retry_err}")
            raise ssl_err


class _TruststoreAdapter(requests.adapters.HTTPAdapter):
    """Adapter que injeta um SSLContext customizado (ex.: truststore) no urllib3."""

    def __init__(self, ssl_context, *args, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)


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


def _show_info_box(title: str, msg: str):
    """
    Mostra MessageBox de INFORMAÇÃO nativa do Windows.
    """
    if platform.system().lower() != "windows":
        return
    try:
        import ctypes
        MB_OK = 0x00000000
        MB_ICONINFORMATION = 0x00000040
        MB_TOPMOST = 0x00040000
        ctypes.windll.user32.MessageBoxW(0, msg, title, MB_OK | MB_ICONINFORMATION | MB_TOPMOST)
    except Exception:
        pass


def _is_program_files_install() -> Optional[str]:
    """
    Se o executável atual estiver sob Program Files, devolve o path — indica
    instalação herdada (feita por admin). Usuário sem privilégio não conseguirá
    sobrescrever e o Inno Setup vai falhar com "Acesso negado".
    """
    if platform.system().lower() != "windows":
        return None
    try:
        exe = os.path.abspath(sys.executable).lower()
        candidates = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("PROGRAMW6432", r"C:\Program Files"),
        ]
        for root in candidates:
            if root and exe.startswith(os.path.abspath(root).lower() + os.sep):
                return sys.executable
    except Exception:
        pass
    return None


def _unblock_file(path: str):
    """
    Remove o alternate data stream Zone.Identifier (Mark of the Web) que o
    Windows coloca em arquivos baixados. Sem isso, AppLocker/SmartScreen em
    ambiente corporativo podem abortar a execução com "Acesso negado".
    Best-effort — falhas são logadas mas não bloqueiam o fluxo.
    """
    if platform.system().lower() != "windows":
        return
    try:
        # Forma direta: apagar o ADS via API do Windows.
        zone_stream = path + ":Zone.Identifier"
        try:
            if os.path.exists(zone_stream):
                os.remove(zone_stream)
                _log("Zone.Identifier removido via os.remove.")
                return
        except Exception:
            pass
        # Fallback: PowerShell Unblock-File.
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-Command", f'Unblock-File -LiteralPath "{path}"'],
            check=False,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        _log("Unblock-File executado via PowerShell.")
    except Exception as e:
        _log(f"_unblock_file falhou (ignorando): {e}")


def _format_user_error(exc: BaseException) -> str:
    """
    Converte exceção técnica em mensagem acionável em português.
    """
    log_hint = f"\n\nDetalhes técnicos em: {PYTHON_LOG_PATH}"
    if isinstance(exc, requests.exceptions.SSLError):
        return (
            "Falha ao validar o certificado HTTPS do GitHub.\n\n"
            "Se você está em uma rede corporativa, peça ao TI para liberar "
            "o acesso a api.github.com e github.com (ou instalar a CA da empresa "
            "no Windows)." + log_hint
        )
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "Tempo esgotado ao conectar ao GitHub. Verifique sua conexão." + log_hint
    if isinstance(exc, requests.exceptions.ConnectionError):
        return (
            "Não foi possível conectar ao GitHub. Verifique sua internet "
            "e, em rede corporativa, se api.github.com está liberado."
            + log_hint
        )
    if isinstance(exc, PermissionError):
        return (
            "Permissão negada ao gravar o arquivo de atualização. "
            "Feche antivírus/antimalware e tente novamente." + log_hint
        )
    return f"Ocorreu um erro durante a atualização:\n\n{exc}" + log_hint


class UpdateService:
    @staticmethod
    def get_latest_release() -> Tuple[Optional[str], Optional[str]]:
        """
        Returns (version_tag, download_url) for the latest release on GitHub.
        Example: ('v1.0.1', 'https://github.com/...')
        """
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            resp = _http_get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                tag = data.get("tag_name", "")

                # Logic to find the correct asset for the current OS
                assets = data.get("assets", [])
                system = platform.system().lower() # 'windows', 'darwin' (mac)

                download_url = None

                # Priority: SIC_Setup.exe (Professional Installer)
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if system == "windows" and "setup" in name and name.endswith(".exe"):
                        download_url = asset.get("browser_download_url")
                        break

                # Fallback: ZIP or single EXE
                if not download_url:
                    for asset in assets:
                        name = asset.get("name", "").lower()
                        if system == "windows" and "windows" in name and (".exe" in name or ".zip" in name):
                            download_url = asset.get("browser_download_url")
                            break
                        elif system == "darwin" and ("mac" in name or "darwin" in name or "macos" in name) and (".dmg" in name or ".zip" in name or ".app" in name):
                            download_url = asset.get("browser_download_url")
                            break

                return tag, download_url
        except Exception as e:
            _log(f"Update check failed: {e}")
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
        Downloads the file and initiates the professional installer (Windows)
        or script-based swap (Mac/Legacy).
        """
        global PYTHON_LOG_PATH

        # Começa um log novo para esta tentativa
        try:
            if os.path.exists(PYTHON_LOG_PATH):
                os.remove(PYTHON_LOG_PATH)
        except Exception:
            pass

        _log("=" * 60)
        _log(f"download_and_install() iniciado — {APP_NAME} v{VERSION}")
        _log(f"URL: {download_url}")
        _log(f"sys.executable: {sys.executable}")
        _log(f"frozen: {getattr(sys, 'frozen', False)}")

        # Pré-voo: se a instalação atual está em Program Files, o Inno Setup
        # vai tentar sobrescrever lá e falhar com "Acesso negado" para qualquer
        # usuário sem admin. Melhor abortar antes com mensagem acionável.
        legacy_path = _is_program_files_install()
        if legacy_path:
            _log(f"Instalação herdada detectada em: {legacy_path}. Abortando update automático.")
            _show_error_box(
                f"{APP_NAME} — Atualização bloqueada",
                (
                    "Sua instalação atual do SIC está em uma pasta protegida:\n\n"
                    f"{legacy_path}\n\n"
                    "Atualizar essa instalação requer permissão de administrador, "
                    "que não está disponível no seu usuário.\n\n"
                    "Peça ao TI para DESINSTALAR o SIC atual (Painel de Controle > "
                    "Programas). A próxima instalação será feita automaticamente "
                    "na sua pasta de usuário e todas as futuras atualizações "
                    "funcionarão sem precisar de administrador."
                ),
            )
            return

        temp_dir = tempfile.gettempdir()
        filename = download_url.split("/")[-1]
        target_path = os.path.join(temp_dir, filename)

        try:
            _log(f"Baixando para {target_path}...")
            resp = _http_get(download_url, stream=True)
            resp.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            _log("Download concluído.")

            is_windows = platform.system().lower() == "windows"

            if is_windows and filename.lower().endswith(".exe"):
                # Remove Mark-of-the-Web antes de lançar — evita bloqueio por
                # SmartScreen/AppLocker em ambientes corporativos.
                _unblock_file(target_path)

                # ── Windows Update Guardian (PowerShell) ──────────────────
                _log("Gerando Script Guardião em PowerShell (Superior)...")

                ps_script_path = os.path.join(temp_dir, "sic_update_guardian.ps1")
                ps_log_path = os.path.join(temp_dir, "sic_update_ps.log")

                # Escapa aspas para o PowerShell
                escaped_target = target_path.replace('"', '`"')
                escaped_log = ps_log_path.replace('"', '`"')
                escaped_exe = sys.executable.replace('"', '`"')

                # Script PowerShell robusto com log e tratamento de erro
                ps_content = f"""
$ErrorActionPreference = "Stop"
$log = "{escaped_log}"
function Log($m) {{ "[" + (Get-Date -Format "HH:mm:ss") + "] $m" | Out-File -FilePath $log -Append -Encoding utf8 }}

try {{
    Log "--- Iniciando Monitor de Atualização ---"
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    $appName = "{APP_NAME}"
    $installer = "{escaped_target}"
    $currentExe = "{escaped_exe}"

    # Remove Mark-of-the-Web caso o strip em Python não tenha pegado.
    try {{ Unblock-File -LiteralPath $installer -ErrorAction SilentlyContinue }} catch {{}}

    Log "Aguardando encerramento total do SIC..."
    # Aguarda até 15s pelo release do handle do SIC.exe — o instalador
    # precisa sobrescrevê-lo, e se ainda estiver aberto dá "Acesso negado".
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {{
        try {{
            if (Test-Path $currentExe) {{
                $fs = [System.IO.File]::Open($currentExe, 'Open', 'Read', 'None')
                $fs.Close()
                Log "SIC.exe liberado."
                break
            }} else {{
                break
            }}
        }} catch {{
            Start-Sleep -Milliseconds 500
        }}
    }}
    Start-Sleep -Seconds 2

    $form = New-Object Windows.Forms.Form
    $form.Text = "Atualização do $appName"
    $form.Size = New-Object Drawing.Size(420, 160)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.MinimizeBox = $false
    $form.TopMost = $true

    $label = New-Object Windows.Forms.Label
    $label.Location = New-Object Drawing.Point(20, 30)
    $label.Size = New-Object Drawing.Size(380, 50)
    $label.Text = "O $appName está sendo atualizado para uma nova versão.`nPor favor, aguarde a conclusão da barra de progresso..."
    $label.TextAlign = "MiddleCenter"
    $label.Font = New-Object Drawing.Font("Segoe UI", 10)
    $form.Controls.Add($label)

    $form.Show()
    $form.Refresh()

    if (Test-Path $installer) {{
        Log "Lançando instalador: $installer"
        # Lança o instalador em modo SILENT e ESPERA terminar.
        # Não usamos -Verb RunAs porque o Inno Setup está configurado com
        # PrivilegesRequired=lowest — instala na pasta do usuário sem UAC.
        $p = Start-Process -FilePath $installer -ArgumentList "/SILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS" -PassThru -Wait
        Log "Instalador finalizado com código: $($p.ExitCode)"
        if ($p.ExitCode -ne 0) {{
            throw "Instalador retornou código $($p.ExitCode). Veja o log do Inno Setup em %TEMP%\\Setup Log*.txt."
        }}
    }} else {{
        throw "Instalador não encontrado em: $installer"
    }}

    $form.Hide()
    Log "Notificando sucesso."
    [Windows.Forms.MessageBox]::Show("A atualização foi concluída com sucesso!`n`nVocê já pode abrir o $appName agora.", "SIC — Atualização Concluída", [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Information)
    $form.Close()

}} catch [System.UnauthorizedAccessException] {{
    $err = $_.Exception.Message
    Log "ACESSO NEGADO: $err"
    [Windows.Forms.MessageBox]::Show("Não foi possível atualizar o $appName porque o Windows bloqueou a escrita:`n`n$err`n`nIsto costuma acontecer quando:`n  1) Uma versão antiga do SIC está instalada em 'Arquivos de Programas' (peça ao TI para desinstalar).`n  2) O antivírus está bloqueando o instalador.`n  3) O SIC.exe ainda está em uso — feche-o e tente de novo.`n`nLog: $log", "SIC — Erro de Atualização", [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Error)
}} catch {{
    $err = $_.Exception.Message
    Log "ERRO CRÍTICO: $err"
    [Windows.Forms.MessageBox]::Show("Ocorreu um erro durante a atualização:`n`n$err`n`nConsulte o log em: $log", "SIC — Erro de Atualização", [Windows.Forms.MessageBoxButtons]::OK, [Windows.Forms.MessageBoxIcon]::Error)
}} finally {{
    Log "--- Fim do Script ---"
}}
"""
                try:
                    # Usamos 'utf-8-sig' para que o PowerShell 5.1 identifique corretmente
                    # arquivos com acentos (BOM) no caminho.
                    with open(ps_script_path, "w", encoding="utf-8-sig") as f:
                        f.write(ps_content)

                    _log(f"Script salvo em {ps_script_path}. Lançando via powershell.exe...")

                    # Lança o PowerShell como processo destacado
                    # Removido Hidden para o usuário ver se houver erro fatal de console (opcional, mas ajuda no debug)
                    cmd = f'powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps_script_path}"'
                    subprocess.Popen(
                        cmd,
                        shell=True,
                        creationflags=subprocess.DETACHED_PROCESS
                    )

                    _log("Guardião lançado. Encerrando SIC.")
                    os._exit(0)
                except Exception as ex:
                    _log(f"Erro ao lançar Guardião: {ex}")
                    subprocess.Popen(f'"{target_path}" /SILENT', shell=True)
                    os._exit(0)

            elif is_windows and filename.lower().endswith(".zip"):
                # ── Legacy ZIP logic (Fallback) ────────────────────────────
                _log("Usando fallback ZIP logic...")
                import zipfile, shutil
                extract_dir = os.path.join(temp_dir, "sic_update_extracted")
                if os.path.exists(extract_dir): shutil.rmtree(extract_dir)
                os.makedirs(extract_dir)

                with zipfile.ZipFile(target_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                new_exe = None
                for root, _, files in os.walk(extract_dir):
                    for f in files:
                        if f.lower() == "sic.exe":
                            new_exe = os.path.join(root, f)
                            break
                    if new_exe: break

                if new_exe:
                    UpdateService._legacy_windows_swap(new_exe)

            elif not is_windows:
                # ── Mac Update logic ──────────────────────────────────────
                _log("Mac update logic...")
                script_path = os.path.join(temp_dir, "sic_update.sh")
                current_app = sys.executable
                while current_app.endswith(".app/Contents/MacOS/SIC"):
                    current_app = os.path.dirname(os.path.dirname(os.path.dirname(current_app)))
                    break

                with open(script_path, "w") as f:
                    f.write(f"#!/bin/bash\nsleep 2\nrm -rf \"{current_app}\"\nmv -f \"{target_path}\" \"{current_app}\"\nopen \"{current_app}\"")
                os.chmod(script_path, 0o755)
                subprocess.Popen(["/bin/bash", script_path], start_new_session=True)
                os._exit(0)

        except Exception as e:
            _log(f"Erro na instalação: {e}")
            _log(traceback.format_exc())
            _show_error_box(f"{APP_NAME} — Erro de Atualização", _format_user_error(e))

    @staticmethod
    def _legacy_windows_swap(new_file_path: str):
        """Simplest possible swap using start explorer/cmd for old ZIP flow"""
        current_exe = sys.executable
        bat_path = os.path.join(tempfile.gettempdir(), "sic_legacy_swap.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\ntimeout /t 2 /nobreak\nmove /y "{new_file_path}" "{current_exe}"\nstart "" "{current_exe}"\nexit')
        os.startfile(bat_path)
        os._exit(0)
