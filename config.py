import os
import logging

class Config:
    # App Info
    APP_NAME = "AutoPhoneFarm"
    VERSION = "1.0.0"
    
    # Server settings
    HOST = "127.0.0.1"
    PORT = 5000
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    DATABASE_PATH = os.path.join(DATA_DIR, "database.db")
    LOG_DIR = os.path.join(DATA_DIR, "logs")
    SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
    SCRIPT_DIR = os.path.join(DATA_DIR, "scripts")
    
    # ADB Configuration
    ADB_PATH = "adb" # User doesn't have ADB yet, we will auto-detect or use system ADB
    
    @classmethod
    def init_app(cls):
        """Initialize application environment"""
        # Create directories if they don't exist
        for directory in [cls.DATA_DIR, cls.LOG_DIR, cls.SCREENSHOT_DIR, cls.SCRIPT_DIR]:
            os.makedirs(directory, exist_ok=True)
            
        # Configure basic logging
        log_file = os.path.join(cls.LOG_DIR, "app.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
