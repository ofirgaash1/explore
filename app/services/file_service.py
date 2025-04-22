from pathlib import Path
from .cache_service import cache, load_json_file
import os

class FileService:
    def __init__(self, app):
        """Initialize the file service with the Flask app"""
        self.app = app
        
        # Use the data directory from app config, or fall back to default
        data_dir = app.config.get('DATA_DIR', os.path.join(app.root_path, '..', 'data'))
        
        # Convert string paths to Path objects
        self.data_dir = Path(data_dir)
        self.json_dir = self.data_dir / 'json'
        self.audio_dir = self.data_dir / 'audio'
        
        # Create directories if they don't exist
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Cache for available files
        self._available_files = None
    
    def get_available_files(self, force_refresh=False):
        if not force_refresh and not cache.should_refresh():
            return cache.get_files_cache()
            
        json_files = {}
        
        for item_path in Path(self.json_dir).iterdir():
            base_name = item_path.name
            if item_path.is_file() and base_name.endswith('.json'):
                base_name = base_name[:-5]
                
            json_path = self._find_json_file(item_path)
            if not json_path:
                continue
                
            audio_path = self._find_audio_file(base_name)
            if audio_path:
                json_files[base_name] = {
                    'json_path': str(json_path),
                    'audio_path': str(audio_path),
                    'audio_format': audio_path.suffix[1:],
                    'last_modified': json_path.stat().st_mtime
                }

        cache.update_files_cache(json_files)
        return json_files
    
    def _find_json_file(self, path):
        if path.is_file():
            return path
        if path.is_dir():
            transcript_path = path / "full_transcript.json"
            if transcript_path.exists():
                return transcript_path
        return None
    
    def _find_audio_file(self, base_name):
        for ext in ['.opus']:#, '.mp3']:
            audio_path = self.audio_dir / f"{base_name}{ext}"
            if audio_path.exists():
                return audio_path
        return None 