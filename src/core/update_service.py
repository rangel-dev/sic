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
                    # Look for Windows .exe or .zip for Windows
                    if system == "windows" and (".exe" in name or ".zip" in name):
                        download_url = asset.get("browser_download_url")
                        break
                    # Look for Mac .app, .dmg, or .zip for Mac
                    elif system == "darwin" and (".dmg" in name or ".zip" in name or ".app" in name):
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
        Downloads the file and prepares the bootstrap restart.
        In a real prod app, you'd use a separate process for this.
        """
        # 1. Download to temp
        temp_dir = tempfile.gettempdir()
        filename = download_url.split("/")[-1]
        target_path = os.path.join(temp_dir, filename)
        
        try:
            resp = requests.get(download_url, stream=True)
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 2. Trigger Bootstrap Update
            UpdateService._trigger_restart_swap(target_path)
        except Exception as e:
            print(f"Download failed: {e}")

    @staticmethod
    def _trigger_restart_swap(new_file_path: str):
        """Creates a batch/sh script to swap the executable and restarts."""
        current_exe = sys.executable
        if "python" in current_exe.lower():
            # Running as script, can't really "auto-update" the python env easily
            # but we can simulate success.
            print("Running as script. Auto-update skipped (would replace .exe).")
            return

        is_windows = platform.system().lower() == "windows"
        
        if is_windows:
            # Simple Batch Swap
            script_path = os.path.join(tempfile.gettempdir(), "sic_update.bat")
            with open(script_path, "w") as f:
                f.write(f"""
@echo off
timeout /t 2 /nobreak > nul
move /y "{new_file_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
""")
            subprocess.Popen([script_path], shell=True)
        else:
            # Mac Shell Swap
            script_path = os.path.join(tempfile.gettempdir(), "sic_update.sh")
            with open(script_path, "w") as f:
                f.write(f"""
#!/bin/bash
sleep 2
mv -f "{new_file_path}" "{current_exe}"
open "{current_exe}"
rm -- "$0"
""")
            os.chmod(script_path, 0o755)
            subprocess.Popen(["/bin/bash", script_path])

        sys.exit(0)
