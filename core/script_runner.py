import time
import logging
import json

logger = logging.getLogger(__name__)

class ScriptRunner:
    def __init__(self, adb_manager):
        self.adb = adb_manager

    def run_script(self, serial, script_data):
        """Run a JSON script on a specific device"""
        try:
            steps = script_data.get('steps', [])
            for i, step in enumerate(steps):
                logger.info(f"Device {serial} - Executing step {i+1}: {step.get('action')}")
                
                success = self._execute_step(serial, step)
                if not success:
                    logger.warning(f"Device {serial} - Step {i+1} failed or returned false. Stopping script.")
                    return False
                    
            return True
        except Exception as e:
            logger.error(f"Error running script on {serial}: {e}")
            return False

    def _execute_step(self, serial, step):
        """Execute a single script step"""
        action = step.get('action')
        
        if action == 'tap':
            x = step.get('x')
            y = step.get('y')
            res = self.adb.tap(serial, x, y)
            return res["success"]
            
        elif action == 'swipe':
            res = self.adb.swipe(
                serial, 
                step.get('x1'), step.get('y1'), 
                step.get('x2'), step.get('y2'),
                step.get('duration', 300)
            )
            return res["success"]
            
        elif action == 'type_text':
            res = self.adb.input_text(serial, step.get('text', ''))
            return res["success"]
            
        elif action == 'wait':
            time.sleep(step.get('seconds', 1))
            return True
            
        elif action == 'shell':
            res = self.adb.shell(serial, step.get('command', ''))
            return res["success"]
            
        elif action == 'find_element':
            # Simplified version: In a real app, you'd dump UI and parse XML with xpath
            # Here we just simulate it
            logger.info(f"Looking for element: {step.get('xpath')}")
            # To actually implement:
            # 1. adb shell uiautomator dump
            # 2. adb pull /sdcard/window_dump.xml
            # 3. parse XML with lxml and find xpath
            time.sleep(1)
            return True # Pretend we found it
            
        elif action == 'loop':
            times = step.get('times', 1)
            sub_steps = step.get('steps', [])
            for _ in range(times):
                for sub_step in sub_steps:
                    if not self._execute_step(serial, sub_step):
                        return False
            return True
            
        else:
            logger.warning(f"Unknown action: {action}")
            return False
