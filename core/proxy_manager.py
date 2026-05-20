import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ProxyManager:
    def __init__(self, database):
        self.db = database

    def get_all_proxies(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proxies ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_proxy(self, proxy_type, host, port, username=None, password=None, notes=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO proxies (type, host, port, username, password, notes) 
               VALUES (?, ?, ?, ?, ?, ?)''',
            (proxy_type, host, port, username, password, notes)
        )
        conn.commit()
        conn.close()
        return True

    def import_proxies(self, text_data, default_type='http'):
        """Import proxies from text (one per line)
           Formats: host:port or host:port:user:pass
        """
        lines = text_data.strip().splitlines()
        added = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(':')
            if len(parts) >= 2:
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    continue
                    
                username = parts[2] if len(parts) >= 3 else None
                password = parts[3] if len(parts) >= 4 else None
                
                self.add_proxy(default_type, host, port, username, password)
                added += 1
                
        return added

    def delete_proxy(self, proxy_id):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM proxies WHERE id = ?', (proxy_id,))
        conn.commit()
        conn.close()
        return True

    def check_proxy(self, proxy_id):
        """Check if proxy is working"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM proxies WHERE id = ?', (proxy_id,))
        proxy = cursor.fetchone()
        
        if not proxy:
            conn.close()
            return False
            
        proxy = dict(proxy)
        
        # Build proxy URL
        if proxy['username'] and proxy['password']:
            auth = f"{proxy['username']}:{proxy['password']}@"
        else:
            auth = ""
            
        proxy_url = f"{proxy['type']}://{auth}{proxy['host']}:{proxy['port']}"
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        status = 'dead'
        try:
            # Try to get public IP via proxy
            res = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
            if res.status_code == 200:
                status = 'alive'
        except Exception:
            status = 'dead'
            
        # Update status
        now = datetime.now().isoformat()
        cursor.execute(
            'UPDATE proxies SET status = ?, last_check = ? WHERE id = ?',
            (status, now, proxy_id)
        )
        conn.commit()
        conn.close()
        
        return status == 'alive'
