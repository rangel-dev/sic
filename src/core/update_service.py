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
            with open(script_path, "w") as f:
                f.write(f"""@echo off
:loop
timeout /t 1 /nobreak > nul
tasklist | find /i "SIC.exe" > nul
if not errorlevel 1 goto loop
move /y "{new_file_path}" "{current_exe}"
rem Aguarda 3 s para o Windows comprometer o arquivo no disco antes de executar.
rem Sem esse delay o bootloader do PyInstaller falha ao ler o proprio .exe
rem com "failed to load python dll / LoadLibrary: modulo nao encontrado".
timeout /t 3 /nobreak > nul
start "" "{current_exe}"
del "%~f0"
""")
            subprocess.Popen([script_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
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
sleep 2
rm -rf "{app_root}"
mv -f "{new_file_path}" "{app_root}"
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
