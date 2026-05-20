import threading
import time
import logging
import os
from config import Config

logger = logging.getLogger(__name__)

class DeviceManager:
    def __init__(self, adb_manager, database):
        self.adb = adb_manager
        self.db = database
        self.is_scanning = False
        self.scan_thread = None
        self.scan_interval = 5  # seconds

    def start_scanner(self):
        """Start background thread to scan devices"""
        if self.is_scanning:
            return
            
        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Device scanner started")

    def stop_scanner(self):
        """Stop background scanning"""
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
        logger.info("Device scanner stopped")

    def _scan_loop(self):
        while self.is_scanning:
            try:
                self.scan_devices()
            except Exception as e:
                logger.error(f"Error during device scan: {e}")
            time.sleep(self.scan_interval)

    def scan_devices(self):
        """Scan connected devices and update database"""
        connected_devices = self.adb.get_devices()
        connected_serials = [d['serial'] for d in connected_devices]
        
        # Mark missing devices as offline
        db_devices = self.db.get_all_devices()
        for db_dev in db_devices:
            if db_dev['serial'] not in connected_serials and db_dev['status'] != 'offline':
                self.db.add_or_update_device({
                    'serial': db_dev['serial'],
                    'status': 'offline'
                })
        
        # Add or update connected devices
        for d in connected_devices:
            serial = d['serial']
            
            # If it's a newly connected device, get full info
            existing = self.db.get_device(serial)
            if not existing or existing['status'] == 'offline':
                logger.info(f"New device detected: {serial}")
                info = self.adb.get_device_info(serial)
                device_data = {
                    'serial': serial,
                    'status': d['status'],
                    'name': f"Device {serial[-4:]}", # Default name
                }
                device_data.update(info)
                self.db.add_or_update_device(device_data)
            else:
                # Just update status and last_seen
                self.db.add_or_update_device({
                    'serial': serial,
                    'status': d['status']
                })
                
    def get_device_screenshot(self, serial):
        """Take screenshot and return the path"""
        filename = f"screen_{serial}.png"
        save_path = os.path.join(Config.SCREENSHOT_DIR, filename)
        
        res = self.adb.screencap(serial, save_path)
        if res["success"]:
            return save_path
        return None
        
    def refresh_device_info(self, serial):
        """Force refresh battery, IP, etc."""
        info = self.adb.get_device_info(serial)
        if info:
            info['serial'] = serial
            self.db.add_or_update_device(info)
            return True
        return False
