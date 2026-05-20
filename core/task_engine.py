import concurrent.futures
import threading
import logging
import json
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskEngine:
    def __init__(self, adb_manager, database):
        self.adb = adb_manager
        self.db = database
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=20)
        self.active_tasks = {} # task_id -> future

    def get_all_tasks(self):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for r in rows:
            t = dict(r)
            if t['target_devices']:
                try:
                    t['target_devices'] = json.loads(t['target_devices'])
                except:
                    t['target_devices'] = []
            tasks.append(t)
        return tasks

    def create_task(self, name, task_type, target_devices, script_data=None):
        """Create a new task in database"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        devices_json = json.dumps(target_devices)
        script_json = json.dumps(script_data) if script_data else None
        
        cursor.execute(
            '''INSERT INTO tasks (name, type, target_devices, script_data) 
               VALUES (?, ?, ?, ?)''',
            (name, task_type, devices_json, script_json)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        self.db.add_log('INFO', 'TaskEngine', f'Created task {task_id}: {name}', task_id=task_id)
        return task_id

    def _update_task_status(self, task_id, status, progress=None, result=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        fields = ["status = ?"]
        values = [status]
        
        if progress is not None:
            fields.append("progress = ?")
            values.append(progress)
            
        if result is not None:
            fields.append("result = ?")
            values.append(json.dumps(result))
            
        if status == 'running':
            fields.append("started_at = ?")
            values.append(now)
        elif status in ['completed', 'failed', 'stopped']:
            fields.append("completed_at = ?")
            values.append(now)
            
        values.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()
        conn.close()

    def _execute_task(self, task_id, task_type, target_devices, script_data):
        """Internal execution method running in a thread"""
        self._update_task_status(task_id, 'running', progress=0)
        self.db.add_log('INFO', 'TaskEngine', f'Task {task_id} started on {len(target_devices)} devices', task_id=task_id)
        
        results = {}
        total = len(target_devices)
        completed = 0
        
        # We can also use thread pool to run devices in parallel
        # But for simplicity in this script runner, we do it sequentially or use nested futures
        
        for serial in target_devices:
            # Check if task was stopped
            if task_id not in self.active_tasks:
                self.db.add_log('WARN', 'TaskEngine', f'Task {task_id} was stopped by user', task_id=task_id)
                self._update_task_status(task_id, 'stopped', result=results)
                return
                
            try:
                # Mark device as busy
                self.db.add_or_update_device({'serial': serial, 'status': 'busy'})
                
                device_result = {"success": False, "error": "Unknown task type"}
                
                if task_type == 'INSTALL_APP':
                    apk_path = script_data.get('apk_path')
                    if apk_path:
                        device_result = self.adb.install_apk(serial, apk_path)
                    else:
                        device_result["error"] = "Missing apk_path"
                        
                elif task_type == 'REBOOT':
                    device_result = self.adb.reboot(serial)
                    
                elif task_type == 'SHELL_CMD':
                    cmd = script_data.get('command')
                    if cmd:
                        device_result = self.adb.shell(serial, cmd)
                    else:
                        device_result["error"] = "Missing command"
                        
                elif task_type == 'RUN_SCRIPT':
                    # Placeholder for script runner
                    time.sleep(2) # Simulate work
                    device_result = {"success": True, "data": "Script executed", "error": None}
                    
                results[serial] = device_result
                
            except Exception as e:
                results[serial] = {"success": False, "error": str(e)}
                
            finally:
                # Mark device as online again
                self.db.add_or_update_device({'serial': serial, 'status': 'online'})
                
            completed += 1
            progress = int((completed / total) * 100)
            self._update_task_status(task_id, 'running', progress=progress)
            
        # Task done
        has_errors = any(not r.get("success", False) for r in results.values())
        final_status = 'failed' if has_errors else 'completed'
        
        self._update_task_status(task_id, final_status, progress=100, result=results)
        self.db.add_log('INFO', 'TaskEngine', f'Task {task_id} finished with status: {final_status}', task_id=task_id)
        
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    def start_task(self, task_id):
        """Start a task execution"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return False
            
        if task['status'] == 'running':
            return False
            
        try:
            target_devices = json.loads(task['target_devices'])
            script_data = json.loads(task['script_data']) if task['script_data'] else {}
        except:
            return False
            
        # Submit to thread pool
        future = self.executor.submit(
            self._execute_task, 
            task_id, 
            task['type'], 
            target_devices, 
            script_data
        )
        self.active_tasks[task_id] = future
        return True

    def stop_task(self, task_id):
        """Stop a running task"""
        if task_id in self.active_tasks:
            # We just remove it from active_tasks. The worker thread will check this and abort.
            del self.active_tasks[task_id]
            self._update_task_status(task_id, 'stopped')
            return True
        return False
        
    def delete_task(self, task_id):
        self.stop_task(task_id)
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        return True
