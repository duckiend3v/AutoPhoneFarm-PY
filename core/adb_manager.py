import subprocess
import os
import logging
import json
import re
from config import Config

logger = logging.getLogger(__name__)

class ADBManager:
    def __init__(self, adb_path="adb"):
        self.adb_path = adb_path
        self._check_adb()

    def _check_adb(self):
        """Check if ADB is available, otherwise try to use system adb"""
        try:
            result = subprocess.run([self.adb_path, "version"], capture_output=True, text=True, timeout=5)
            logger.info(f"ADB is ready: {result.stdout.splitlines()[0]}")
        except Exception as e:
            logger.warning(f"ADB not found at {self.adb_path}, falling back to system 'adb'. Error: {e}")
            self.adb_path = "adb"

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
        """Get detailed info for a device"""
        info = {}
        
        # Get Model
        res = self.shell(serial, "getprop ro.product.model")
        if res["success"]:
            info["model"] = res["data"]
            
        # Get Android Version
        res = self.shell(serial, "getprop ro.build.version.release")
        if res["success"]:
            info["android_version"] = res["data"]
            
        # Get Battery
        res = self.shell(serial, "dumpsys battery")
        if res["success"]:
            match = re.search(r"level: (\d+)", res["data"])
            if match:
                info["battery"] = int(match.group(1))
                
        # Get IP Address (WiFi)
        res = self.shell(serial, "ip route")
        if res["success"]:
            match = re.search(r"src (\d+\.\d+\.\d+\.\d+)", res["data"])
            if match:
                info["ip_address"] = match.group(1)
                
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
