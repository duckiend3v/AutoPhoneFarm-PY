import subprocess
import os
import sys
import logging
import json
import re
from config import Config

logger = logging.getLogger(__name__)

class ADBManager:
    def __init__(self, adb_path="adb"):
        self.adb_path = adb_path
        self._check_adb()

    def _download_adb(self):
        """Auto-download ADB from official Google repository"""
        import urllib.request
        import zipfile
        import shutil
        
        adb_dir = os.path.join(Config.DATA_DIR, "adb")
        os.makedirs(adb_dir, exist_ok=True)
        
        zip_path = os.path.join(adb_dir, "platform-tools.zip")
        extracted_path = os.path.join(adb_dir, "platform-tools")
        
        # URL for Windows platform tools
        url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        if os.name != 'nt':
            # Linux / macOS fallback
            url = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
            if sys.platform == 'darwin':
                url = "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
        
        logger.info(f"Downloading ADB from {url}...")
        try:
            # Download zip file
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=60) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
            logger.info("Extracting ADB...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(adb_dir)
                
            # Clean up zip file
            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            local_adb = os.path.join(extracted_path, "adb.exe" if os.name == 'nt' else "adb")
            if os.path.exists(local_adb):
                # Set execute permissions for Unix
                if os.name != 'nt':
                    os.chmod(local_adb, 0o755)
                logger.info(f"ADB successfully downloaded and extracted to {local_adb}")
                return local_adb
        except Exception as e:
            logger.error(f"Failed to auto-download ADB: {e}")
        return None

    def _check_adb(self):
        """Check if ADB is available, otherwise try local, and auto-download if missing"""
        # 1. Try config/system adb
        try:
            result = subprocess.run([self.adb_path, "version"], capture_output=True, text=True, timeout=5)
            logger.info(f"ADB is ready: {result.stdout.splitlines()[0]}")
            return
        except Exception as e:
            logger.warning(f"ADB not found at {self.adb_path}, checking local cache...")
            
        # 2. Check if already downloaded locally
        local_adb_dir = os.path.join(Config.DATA_DIR, "adb", "platform-tools")
        local_adb = os.path.join(local_adb_dir, "adb.exe" if os.name == 'nt' else "adb")
        if os.path.exists(local_adb):
            self.adb_path = local_adb
            logger.info(f"Using cached local ADB: {self.adb_path}")
            return
            
        # 3. Auto-download if not present
        downloaded_adb = self._download_adb()
        if downloaded_adb:
            self.adb_path = downloaded_adb
            Config.ADB_PATH = downloaded_adb
        else:
            logger.error("Could not find or download ADB. ADB operations will fail.")
            self.adb_path = "adb" # fallback

    def _run_cmd(self, args, timeout=30):
        """Execute an ADB command and return the result"""
        cmd = [self.adb_path] + args
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0:
                return {"success": True, "data": result.stdout.strip(), "error": None}
            else:
                return {"success": False, "data": None, "error": result.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {"success": False, "data": None, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def execute(self, serial, command, timeout=30):
        """Execute an adb command on a specific device"""
        if isinstance(command, str):
            command = command.split()
        return self._run_cmd(["-s", serial] + command, timeout)

    def shell(self, serial, command, timeout=30):
        """Execute an adb shell command on a specific device"""
        if isinstance(command, str):
            command = command.split()
        return self.execute(serial, ["shell"] + command, timeout)

    def get_devices(self):
        """Get list of connected devices"""
        result = self._run_cmd(["devices"])
        if not result["success"]:
            return []
            
        devices = []
        lines = result["data"].splitlines()
        for line in lines[1:]: # Skip first line "List of devices attached"
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                devices.append({
                    "serial": serial,
                    "status": "online" if status == "device" else status
                })
        return devices

    def get_device_info(self, serial):
        """Get detailed info for a device using a single combined shell command"""
        info = {
            "model": "Unknown",
            "android_version": "Unknown",
            "battery": 0,
            "ip_address": "Unknown"
        }
        
        # Single batched command to fetch model, android version, battery and ip
        cmd = "getprop ro.product.model; echo '[SPLIT]'; getprop ro.build.version.release; echo '[SPLIT]'; dumpsys battery; echo '[SPLIT]'; ip route"
        res = self.shell(serial, cmd, timeout=10)
        
        if not res["success"] or not res["data"]:
            return info
            
        parts = res["data"].split('[SPLIT]')
        
        # Parse model
        if len(parts) > 0:
            info["model"] = parts[0].strip() or "Unknown"
            
        # Parse android version
        if len(parts) > 1:
            info["android_version"] = parts[1].strip() or "Unknown"
            
        # Parse battery
        if len(parts) > 2:
            battery_data = parts[2]
            match = re.search(r"level:\s*(\d+)", battery_data, re.IGNORECASE)
            if match:
                info["battery"] = int(match.group(1))
            else:
                info["battery"] = 100  # Default
                
        # Parse IP Address
        if len(parts) > 3:
            ip_data = parts[3]
            match = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", ip_data)
            if match:
                info["ip_address"] = match.group(1)
            else:
                # Try fallback parsing for IP (find any IP-like string in ip route output)
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", ip_data)
                if match:
                    info["ip_address"] = match.group(1)
                else:
                    info["ip_address"] = "Offline"
                    
        return info

    def screencap(self, serial, save_path):
        """Take a screenshot and save to host"""
        try:
            # Capture to device tmp
            remote_path = "/data/local/tmp/screen.png"
            res = self.shell(serial, f"screencap -p {remote_path}")
            if not res["success"]:
                return res
                
            # Pull to host
            res = self.execute(serial, ["pull", remote_path, save_path])
            if not res["success"]:
                return res
                
            # Cleanup remote
            self.shell(serial, f"rm {remote_path}")
            return {"success": True, "data": save_path, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def tap(self, serial, x, y):
        """Tap on screen coordinates"""
        return self.shell(serial, f"input tap {x} {y}")

    def swipe(self, serial, x1, y1, x2, y2, duration=300):
        """Swipe on screen"""
        return self.shell(serial, f"input swipe {x1} {y1} {x2} {y2} {duration}")

    def input_text(self, serial, text):
        """Input text (escapes spaces)"""
        # Simple escaping for spaces
        escaped_text = text.replace(" ", "%s")
        return self.shell(serial, f"input text {escaped_text}")
        
    def install_apk(self, serial, apk_path):
        """Install an APK file"""
        return self.execute(serial, ["install", "-r", "-g", apk_path], timeout=120)
        
    def reboot(self, serial):
        """Reboot the device"""
        return self.execute(serial, ["reboot"])

    def _download_scrcpy(self):
        """Auto-download scrcpy if not available"""
        import urllib.request
        import zipfile
        import shutil
        
        scrcpy_dir = os.path.join(Config.DATA_DIR, "scrcpy")
        os.makedirs(scrcpy_dir, exist_ok=True)
        
        zip_path = os.path.join(scrcpy_dir, "scrcpy.zip")
        extracted_path = os.path.join(scrcpy_dir, "scrcpy-win64-v2.4")
        
        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-win64-v2.4.zip"
        
        logger.info(f"Downloading scrcpy from {url}...")
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=60) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
            logger.info("Extracting scrcpy...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(scrcpy_dir)
                
            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            local_scrcpy = os.path.join(extracted_path, "scrcpy.exe")
            if os.path.exists(local_scrcpy):
                logger.info(f"scrcpy successfully downloaded and extracted to {local_scrcpy}")
                return local_scrcpy
        except Exception as e:
            logger.error(f"Failed to auto-download scrcpy: {e}")
        return None

    def start_mirror(self, serial):
        """Start mirroring and live control using scrcpy"""
        if os.name != 'nt':
            return {"success": False, "error": "Direct screen control is currently only supported on Windows hosts."}
            
        scrcpy_dir = os.path.join(Config.DATA_DIR, "scrcpy", "scrcpy-win64-v2.4")
        scrcpy_exe = os.path.join(scrcpy_dir, "scrcpy.exe")
        
        # Check if already downloaded
        if not os.path.exists(scrcpy_exe):
            downloaded = self._download_scrcpy()
            if not downloaded:
                return {"success": False, "error": "scrcpy not found and could not be downloaded."}
            scrcpy_exe = downloaded
            
        # Run scrcpy in background
        try:
            # Set ADB env var so scrcpy uses our downloaded adb.exe
            env = os.environ.copy()
            env["ADB"] = self.adb_path
            
            cmd = [
                scrcpy_exe,
                "-s", serial,
                "--window-title", f"AutoPhoneFarm - Live Control - {serial}",
                "--max-size", "1024",
                "--max-fps", "30"
            ]
            
            # Start process without blocking and without creating console window
            subprocess.Popen(
                cmd,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return {"success": True, "message": f"Direct control window opened for device {serial}."}
        except Exception as e:
            logger.error(f"Failed to launch scrcpy for {serial}: {e}")
            return {"success": False, "error": str(e)}
