import os
import sys
import threading
import webbrowser
import subprocess
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO
import eventlet

# Import core modules
from config import Config
from core.database import Database
from core.adb_manager import ADBManager
from core.device import DeviceManager
from core.task_engine import TaskEngine
from core.proxy_manager import ProxyManager
from core.script_runner import ScriptRunner

# Initialize Config
Config.init_app()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'autophonefarm_secret_key'
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# Initialize Core Services
db = Database(Config.DATABASE_PATH)
adb = ADBManager(Config.ADB_PATH)
device_mgr = DeviceManager(adb, db)
device_mgr.socketio = socketio
task_engine = TaskEngine(adb, db)
proxy_mgr = ProxyManager(db)
script_runner = ScriptRunner(adb)

# ==========================================
# PAGE ROUTES
# ==========================================
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/devices')
def devices_page():
    return render_template('devices.html')

@app.route('/tasks')
def tasks_page():
    return render_template('tasks.html')

@app.route('/accounts')
def accounts_page():
    return render_template('accounts.html')

@app.route('/proxies')
def proxies_page():
    return render_template('proxies.html')

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

# Serve screenshots
@app.route('/data/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(Config.SCREENSHOT_DIR, filename)

# ==========================================
# API ROUTES
# ==========================================

# --- Devices ---
@app.route('/api/devices', methods=['GET'])
def get_devices():
    devices = db.get_all_devices()
    return jsonify({"success": True, "data": devices})

@app.route('/api/devices/scan', methods=['POST'])
def scan_devices():
    device_mgr.scan_devices()
    return jsonify({"success": True, "message": "Scan completed"})

@app.route('/api/devices/<serial>/screenshot', methods=['POST'])
def capture_screenshot(serial):
    path = device_mgr.get_device_screenshot(serial)
    if path:
        filename = os.path.basename(path)
        return jsonify({"success": True, "data": f"/data/screenshots/{filename}"})
    return jsonify({"success": False, "error": "Failed to capture screenshot"})

@app.route('/api/devices/<serial>/reboot', methods=['POST'])
def reboot_device(serial):
    res = adb.reboot(serial)
    return jsonify(res)

@app.route('/api/devices/<serial>/shell', methods=['POST'])
def device_shell(serial):
    cmd = request.json.get('command')
    res = adb.shell(serial, cmd)
    return jsonify(res)

@app.route('/api/devices/<serial>/mirror', methods=['POST'])
def mirror_device(serial):
    res = adb.start_mirror(serial)
    return jsonify(res)

# --- Tasks ---
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = task_engine.get_all_tasks()
    return jsonify({"success": True, "data": tasks})

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    task_id = task_engine.create_task(
        name=data.get('name'),
        task_type=data.get('type'),
        target_devices=data.get('target_devices', []),
        script_data=data.get('script_data')
    )
    return jsonify({"success": True, "data": {"id": task_id}})

@app.route('/api/tasks/<int:task_id>/start', methods=['POST'])
def start_task(task_id):
    success = task_engine.start_task(task_id)
    return jsonify({"success": success})

@app.route('/api/tasks/<int:task_id>/stop', methods=['POST'])
def stop_task(task_id):
    success = task_engine.stop_task(task_id)
    return jsonify({"success": success})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    success = task_engine.delete_task(task_id)
    return jsonify({"success": success})

# --- Accounts ---
@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = db.get_all_accounts()
    return jsonify({"success": True, "data": accounts})

@app.route('/api/accounts', methods=['POST'])
def add_account():
    data = request.json
    success = db.add_account(
        platform=data.get('platform', 'facebook'),
        username=data.get('username'),
        password=data.get('password'),
        email=data.get('email'),
        phone=data.get('phone'),
        cookies=data.get('cookies'),
        token=data.get('token'),
        assigned_device_serial=data.get('assigned_device_serial'),
        notes=data.get('notes')
    )
    return jsonify({"success": success})

@app.route('/api/accounts/<int:account_id>', methods=['DELETE'])
def delete_account(account_id):
    success = db.delete_account(account_id)
    return jsonify({"success": success})

@app.route('/api/accounts/import', methods=['POST'])
def import_accounts():
    text_data = request.json.get('accounts', '')
    platform = request.json.get('platform', 'facebook')
    added = db.import_accounts(text_data, platform)
    return jsonify({"success": True, "message": f"Imported {added} accounts"})

# --- Proxies ---
@app.route('/api/proxies', methods=['GET'])
def get_proxies():
    proxies = proxy_mgr.get_all_proxies()
    return jsonify({"success": True, "data": proxies})

@app.route('/api/proxies/import', methods=['POST'])
def import_proxies():
    text_data = request.json.get('proxies', '')
    default_type = request.json.get('type', 'http')
    added = proxy_mgr.import_proxies(text_data, default_type)
    return jsonify({"success": True, "message": f"Imported {added} proxies"})

@app.route('/api/proxies/<int:proxy_id>', methods=['DELETE'])
def delete_proxy(proxy_id):
    success = proxy_mgr.delete_proxy(proxy_id)
    return jsonify({"success": success})

@app.route('/api/proxies/check_all', methods=['POST'])
def check_all_proxies():
    threading.Thread(target=proxy_mgr.check_all_proxies, daemon=True).start()
    return jsonify({"success": True, "message": "Proxy check started in background"})

@app.route('/api/proxies/clear_dead', methods=['POST'])
def clear_dead_proxies():
    success = proxy_mgr.clear_dead_proxies()
    return jsonify({"success": success})

# --- Logs ---
@app.route('/api/logs', methods=['GET'])
def get_logs():
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    logs = db.get_logs(limit, offset)
    return jsonify({"success": True, "data": logs})

# --- Settings & Database ---
@app.route('/api/settings/adb', methods=['POST'])
def save_adb_settings():
    path = request.json.get('adb_path', 'adb')
    Config.ADB_PATH = path
    adb.adb_path = path
    return jsonify({"success": True})

@app.route('/api/settings/adb/test', methods=['POST'])
def test_adb_settings():
    path = request.json.get('adb_path', 'adb')
    try:
        result = subprocess.run(
            [path, "version"], 
            capture_output=True, 
            text=True, 
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0:
            return jsonify({"success": True, "version": result.stdout.strip().splitlines()[0]})
        return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/database/clear_logs', methods=['POST'])
def clear_logs():
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM logs')
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Logs cleared successfully"})

@app.route('/api/database/backup', methods=['POST'])
def backup_database():
    import shutil
    from datetime import datetime
    backup_name = f"database.backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.db"
    backup_path = os.path.join(Config.DATA_DIR, backup_name)
    shutil.copy2(Config.DATABASE_PATH, backup_path)
    return jsonify({"success": True, "message": f"Backup saved as {backup_name}"})

# ==========================================
# WEBSOCKET
# ==========================================
@socketio.on('connect')
def handle_connect():
    print("Client connected")

def background_emit_stats():
    """Emit stats periodically to connected clients"""
    while True:
        eventlet.sleep(5)
        devices = db.get_all_devices()
        online_count = sum(1 for d in devices if d['status'] == 'online')
        socketio.emit('stats_update', {
            'total_devices': len(devices),
            'online_devices': online_count
        })

# ==========================================
# MAIN
# ==========================================
def open_browser():
    """Try to open Chrome in app mode"""
    url = f"http://{Config.HOST}:{Config.PORT}"
    try:
        # For Windows
        if os.name == 'nt':
            subprocess.Popen(['start', 'chrome', f'--app={url}'], shell=True)
            return
    except:
        pass
    
    # Fallback
    webbrowser.open(url)

if __name__ == '__main__':
    # Start device scanner
    device_mgr.start_scanner()
    
    # Start socketio background task
    eventlet.spawn(background_emit_stats)
    
    # Open browser slightly after server starts
    threading.Timer(1.5, open_browser).start()
    
    print(f"Starting AutoPhoneFarm server at http://{Config.HOST}:{Config.PORT}")
    socketio.run(app, host=Config.HOST, port=Config.PORT, debug=False)
