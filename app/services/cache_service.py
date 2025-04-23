from datetime import datetime, timedelta
from functools import lru_cache
import json

class CacheService:
    def __init__(self, cache_duration=timedelta(minutes=5)):
        self.cache_duration = cache_duration
        self.last_scan_time = None
        self.files_cache = {}
        self.segments_cache = {}
    
    def should_refresh(self):
        if self.last_scan_time is None:
            return True
        return datetime.now() - self.last_scan_time > self.cache_duration
    
    def update_files_cache(self, files):
        self.files_cache = files
        self.last_scan_time = datetime.now()
    
    def get_files_cache(self):
        return self.files_cache
    
    def clear_all(self):
        self.files_cache = {}
        self.segments_cache = {}
        self.last_scan_time = None
        load_json_file.cache_clear()

# Global cache instance
cache = CacheService()

@lru_cache(maxsize=128)
def load_json_file(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {json_path}: {e}")
        return None 
    
