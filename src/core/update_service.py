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

        temp_dir = tempfile.gettempdir()
        filename = download_url.split("/")[-1]
        target_path = os.path.join(temp_dir, filename)

        try:
            _log(f"Baixando para {target_path}...")
            resp = requests.get(download_url, stream=True)
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            _log("Download concluído.")

            is_windows = platform.system().lower() == "windows"
            
            if is_windows and filename.lower().endswith(".exe"):
                # ── Windows Installer (Inno Setup) ──────────────────────────
                _log("Lançando instalador silent...")
                # Flags do Inno Setup:
                # /VERYSILENT: Interface mínima
                # /SUPPRESSMSGBOXES: Sem diálogos
                # /FORCECLOSEAPPLICATIONS: Fecha o SIC se estiver aberto
                args = [
                    target_path, 
                    "/VERYSILENT", 
                    "/SUPPRESSMSGBOXES", 
                    "/FORCECLOSEAPPLICATIONS"
                ]
                
                # Usamos um comando de shell com DETACHED_PROCESS para garantir
                # que o instalador seja lançado de forma independente e o SIC possa fechar.
                cmd = f'"{target_path}" /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS'
                subprocess.Popen(
                    cmd, 
                    shell=True, 
                    creationflags=subprocess.DETACHED_PROCESS
                )
                
                _log("Instalador lançado. Encerrando o app para permitir substituição.")
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
            _show_error_box(f"{APP_NAME} — Erro de Atualização", str(e))

    @staticmethod
    def _legacy_windows_swap(new_file_path: str):
        """Simplest possible swap using start explorer/cmd for old ZIP flow"""
        current_exe = sys.executable
        bat_path = os.path.join(tempfile.gettempdir(), "sic_legacy_swap.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\ntimeout /t 2 /nobreak\nmove /y "{new_file_path}" "{current_exe}"\nstart "" "{current_exe}"\nexit')
        os.startfile(bat_path)
        os._exit(0)
