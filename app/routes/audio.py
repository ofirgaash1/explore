from flask import Blueprint, send_file, current_app
from urllib.parse import unquote
from ..services.file_service import FileService
import os

bp = Blueprint('audio', __name__)

@bp.route('/audio/<path:filename>')
def serve_audio(filename):
    try:
        # Remove any file extension from the filename
        base_name = filename.rsplit('.', 1)[0]
        print(f"Requested audio for base name: {base_name}")
        
        file_service = FileService(current_app)
        available_files = file_service.get_available_files()
        
        # Try to find an exact match first
        if base_name in available_files:
            file_info = available_files[base_name]
            print(f"Found exact match: {file_info['audio_path']}")
            return send_file(file_info['audio_path'])
            
        # If no exact match, try URL-decoded version
        decoded_name = unquote(base_name)
        print(f"Trying decoded name: {decoded_name}")
        
        if decoded_name in available_files:
            file_info = available_files[decoded_name]
            print(f"Found match after decoding: {file_info['audio_path']}")
            return send_file(file_info['audio_path'])
            
        print(f"Available files: {list(available_files.keys())}")
        return f"Audio file not found for {filename}", 404
        
    except Exception as e:
        print(f"Error serving audio file {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 404

@bp.route('/check-audio/<filename>')
def check_audio(filename):
    try:
        file_service = FileService(current_app)
        available_files = file_service.get_available_files()
        
        base_name = filename.rsplit('.', 1)[0]
        if base_name in available_files:
            file_info = available_files[base_name]
            return f"File exists! Size: {os.path.getsize(file_info['audio_path'])} bytes"
            
        return "File not found!", 404
    except Exception as e:
        return f"Error: {str(e)}", 500 