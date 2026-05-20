import threading
import time
import logging
import os
from config import Config

logger = logging.getLogger(__name__)

import concurrent.futures

class DeviceManager:
    def __init__(self, adb_manager, database):
        self.adb = adb_manager
        self.db = database
        self.is_scanning = False
        self.scan_thread = None
        self.scan_interval = 5  # seconds
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=30)
        self.active_queries = set()
        self.socketio = None # Will be set by app.py

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
        """Scan connected devices and update database quickly, then query details in background"""
        connected_devices = self.adb.get_devices()
        connected_serials = [d['serial'] for d in connected_devices]
        
        # Mark missing devices as offline in database
        db_devices = self.db.get_all_devices()
        for db_dev in db_devices:
            if db_dev['serial'] not in connected_serials and db_dev['status'] != 'offline':
                self.db.add_or_update_device({
                    'serial': db_dev['serial'],
                    'status': 'offline'
                })
        
        # Add or update connected devices instantly
        for d in connected_devices:
            serial = d['serial']
            status = d['status']
            existing = self.db.get_device(serial)
            
            # Immediately update status to 'online' in DB to reflect on frontend
            if not existing:
                # Newly detected device: save stub first and trigger background detail fetch
                self.db.add_or_update_device({
                    'serial': serial,
                    'status': status,
                    'name': f"Device {serial[-4:]}", # Default name
                    'model': 'Unknown',
                    'android_version': 'Unknown',
                    'battery': 0,
                    'ip_address': 'Unknown'
                })
                self.executor.submit(self._async_fetch_device_info, serial, status)
            elif existing['status'] == 'offline' or existing['model'] == 'Unknown' or not existing['ip_address'] or existing['ip_address'] == 'Unknown':
                # Device was offline or has missing details: update status and trigger detail query
                self.db.add_or_update_device({
                    'serial': serial,
                    'status': status
                })
                self.executor.submit(self._async_fetch_device_info, serial, status)
            else:
                # Already active, just update status/last_seen to keep it fresh
                self.db.add_or_update_device({
                    'serial': serial,
                    'status': status
                })
                
    def _async_fetch_device_info(self, serial, status):
        """Background thread worker to retrieve detailed device information via ADB"""
        if serial in self.active_queries:
            return
            
        self.active_queries.add(serial)
        try:
            logger.info(f"Querying details for device in background: {serial}")
            info = self.adb.get_device_info(serial)
            
            # Update DB with full details
            device_data = {
                'serial': serial,
                'status': status
            }
            device_data.update(info)
            self.db.add_or_update_device(device_data)
            
            # Push WebSocket notification to trigger frontend update if SocketIO is set
            if self.socketio:
                self.socketio.emit('device_updated', {'serial': serial, 'info': info})
                
            logger.info(f"Successfully loaded details for device: {serial}")
        except Exception as e:
            logger.error(f"Error fetching details for {serial}: {e}")
        finally:
            self.active_queries.remove(serial)
                
    def get_device_screenshot(self, serial):
        """Take screenshot and return the path"""
        filename = f"screen_{serial}.png"
        save_path = os.path.join(Config.SCREENSHOT_DIR, filename)
        
        res = self.adb.screencap(serial, save_path)
        if res["success"]:
            return save_path
        return None
        
    def refresh_device_info(self, serial):
        """Force refresh battery, IP, etc. in a background thread"""
        self.executor.submit(self._async_fetch_device_info, serial, 'online')
        return True
