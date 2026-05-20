import sqlite3
import os
import json
from datetime import datetime

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
        
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create devices table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            serial TEXT PRIMARY KEY,
            name TEXT,
            model TEXT,
            android_version TEXT,
            status TEXT DEFAULT 'offline',
            ip_address TEXT,
            battery INTEGER,
            assigned_proxy_id INTEGER,
            assigned_account_id INTEGER,
            last_seen TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create accounts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            username TEXT,
            password TEXT,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'pending',
            cookies TEXT,
            token TEXT,
            assigned_device_serial TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create proxies table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT DEFAULT 'http',
            host TEXT NOT NULL,
            port INTEGER NOT NULL,
            username TEXT,
            password TEXT,
            status TEXT DEFAULT 'unknown',
            last_check TIMESTAMP,
            country TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create tasks table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            target_devices TEXT, -- JSON array of serials
            script_data TEXT, -- JSON script content
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            result TEXT,
            scheduled_at TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT DEFAULT 'INFO',
            source TEXT,
            message TEXT NOT NULL,
            device_serial TEXT,
            task_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    # --- DEVICES ---
    def get_all_devices(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
        
    def get_device(self, serial):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM devices WHERE serial = ?', (serial,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
        
    def add_or_update_device(self, device_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        serial = device_data.get('serial')
        if not serial:
            return False
            
        cursor.execute('SELECT serial FROM devices WHERE serial = ?', (serial,))
        exists = cursor.fetchone()
        
        now = datetime.now().isoformat()
        
        if exists:
            # Update
            update_fields = []
            values = []
            for key, value in device_data.items():
                if key != 'serial':
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            update_fields.append("last_seen = ?")
            values.append(now)
            values.append(serial)
            
            query = f"UPDATE devices SET {', '.join(update_fields)} WHERE serial = ?"
            cursor.execute(query, values)
        else:
            # Insert
            device_data['last_seen'] = now
            fields = list(device_data.keys())
            placeholders = ['?'] * len(fields)
            values = list(device_data.values())
            
            query = f"INSERT INTO devices ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, values)
            
        conn.commit()
        conn.close()
        return True

    def delete_device(self, serial):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM devices WHERE serial = ?', (serial,))
        conn.commit()
        conn.close()
        return True

    # --- LOGS ---
    def add_log(self, level, source, message, device_serial=None, task_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO logs (level, source, message, device_serial, task_id) VALUES (?, ?, ?, ?, ?)',
            (level, source, message, device_serial, task_id)
        )
        conn.commit()
        conn.close()
        return True
        
    def get_logs(self, limit=100, offset=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM logs ORDER BY created_at DESC LIMIT ? OFFSET ?', (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
