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
from pathlib import Path
from typing import Optional, Tuple
from .version import VERSION, GITHUB_REPO

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
        import zipfile
        
        # 1. Download to temp
        temp_dir = tempfile.gettempdir()
        filename = download_url.split("/")[-1]
        target_zip_path = os.path.join(temp_dir, filename)
        
        try:
            resp = requests.get(download_url, stream=True)
            with open(target_zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 2. Extract Zip (limpa a pasta antes para evitar resíduos de atualizações anteriores)
            import shutil
            extract_dir = os.path.join(temp_dir, "sic_update_extracted")
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)

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
                
            # Find the extracted executable/app
            is_windows = platform.system().lower() == "windows"
            new_file_path = None
            
            if is_windows:
                # Look for SIC.exe
                for root, _, files in os.walk(extract_dir):
                    for name in files:
                        if name.lower().endswith(".exe"):
                            new_file_path = os.path.join(root, name)
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
                print("Failed to find executable in extracted update.")
                return

            # 3. Trigger Bootstrap Update
            UpdateService._trigger_restart_swap(new_file_path)
            
        except Exception as e:
            print(f"Update failed: {e}")

    @staticmethod
    def _trigger_restart_swap(new_file_path: str):
        """Creates a batch/sh script to swap the executable and restarts in a detached state."""
        current_exe = sys.executable
        if "python" in current_exe.lower():
            print("Running as script. Auto-update skipped (would replace .exe).")
            return

        is_windows = platform.system().lower() == "windows"
        
        if is_windows:
            script_path = os.path.join(tempfile.gettempdir(), "sic_update.bat")
            exe_dir = os.path.dirname(current_exe)
            # Escreve o .bat em UTF-8 e declara chcp 65001 dentro dele, para que
            # caminhos com acentos (ex: "Área de Trabalho") não sejam corrompidos
            # pela codepage OEM padrão do cmd.exe.
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(f"""@echo off
chcp 65001 > nul

rem Aguarda o processo principal (bootloader + filho Python) encerrar
:loop
timeout /t 1 /nobreak > nul
tasklist /fi "imagename eq SIC.exe" 2>nul | find /i "SIC.exe" > nul
if not errorlevel 1 goto loop

rem Aguarda o cleanup do diretorio temporario _MEI do PyInstaller
timeout /t 2 /nobreak > nul

rem Substitui o executavel (retenta uma vez se pegar lock residual)
move /y "{new_file_path}" "{current_exe}"
if errorlevel 1 (
    timeout /t 3 /nobreak > nul
    move /y "{new_file_path}" "{current_exe}"
)

rem Aguarda o Windows comprometer o arquivo no disco (write-behind cache)
timeout /t 3 /nobreak > nul

rem Muda para o diretorio do exe e lanca de la, imitando um launch via Explorer.
rem Sem isso o novo processo herda CWD=%TEMP%, o que confunde o bootloader
rem do PyInstaller ao resolver dependencias durante a extracao do _MEI.
cd /d "{exe_dir}"
start "" /D "{exe_dir}" "{current_exe}"

rem Auto-delete
(goto) 2>nul & del "%~f0"
""")
            # DETACHED_PROCESS desacopla o .bat do processo Python que esta morrendo.
            # Sem isso, o novo SIC.exe nasce como "neto" de um processo zumbi e o
            # bootloader do PyInstaller falha ao chamar LoadLibrary no python3xx.dll,
            # exibindo "failed to load python dll / modulo nao encontrado".
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(
                [script_path],
                shell=True,
                creationflags=DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                close_fds=True,
            )
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
        os._exit(0)
