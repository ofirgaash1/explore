from flask import Blueprint, send_file, current_app, request, Response
from urllib.parse import unquote
from ..routes.auth import login_required
import os
import mimetypes
import re
import time
import logging
import uuid
import glob

bp = Blueprint('audio', __name__)
logger = logging.getLogger(__name__)

def send_range_file(path, request_id=None):
    start_time = time.time()
    if request_id:
        logger.info(f"[TIMING] [REQ:{request_id}] Starting to send file: {path}")
    
    range_header = request.headers.get('Range', None)
    if not os.path.exists(path):
        if request_id:
            logger.error(f"[TIMING] [REQ:{request_id}] File not found: {path}")
        return "File not found", 404

    size = os.path.getsize(path)
    content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'

    def generate_chunks():
        chunk_size = 8192  # 8KB chunks
        with open(path, 'rb') as f:
            if range_header:
                # Example Range: bytes=12345-
                byte1, byte2 = 0, None
                m = re.search(r'bytes=(\d+)-(\d*)', range_header)
                if m:
                    byte1 = int(m.group(1))
                    if m.group(2):
                        byte2 = int(m.group(2))
                if byte2 is None:
                    byte2 = size - 1
                length = byte2 - byte1 + 1
                
                if request_id:
                    logger.info(f"[TIMING] [REQ:{request_id}] Serving range request: bytes {byte1}-{byte2}/{size}")
                
                f.seek(byte1)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
            else:
                if request_id:
                    logger.info(f"[TIMING] [REQ:{request_id}] Serving full file: {size} bytes")
                
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

    if range_header:
        m = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if m:
            byte1 = int(m.group(1))
            byte2 = int(m.group(2)) if m.group(2) else size - 1
            length = byte2 - byte1 + 1
            
            resp = Response(generate_chunks(), 206, mimetype=content_type)
            resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
            resp.headers.add('Accept-Ranges', 'bytes')
            resp.headers.add('Content-Length', str(length))
            
            if request_id:
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"[TIMING] [REQ:{request_id}] Range file served in {duration_ms:.2f}ms")
            
            return resp

    # No Range: return full file
    resp = Response(generate_chunks(), 200, mimetype=content_type)
    resp.headers.add('Accept-Ranges', 'bytes')
    resp.headers.add('Content-Length', str(size))
    
    if request_id:
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"[TIMING] [REQ:{request_id}] Full file served in {duration_ms:.2f}ms")
    
    return resp

@bp.route('/audio/<path:filename>')
@login_required
def serve_audio(filename):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    logger.info(f"[TIMING] [REQ:{request_id}] Audio request received for: {filename}")
    
    try:
        # Remove any file extension from the filename
        base_name = filename.rsplit('.', 1)[0]
        logger.info(f"[TIMING] [REQ:{request_id}] Requested audio for base name: {base_name}")
        
        # Get audio directory from config
        audio_dir = current_app.config.get('AUDIO_DIR')
        if not audio_dir:
            raise ValueError("AUDIO_DIR not configured in application")
            
        # Try to find the audio file using glob pattern
        search_pattern = os.path.join(audio_dir, '*', f"{base_name}.opus")
        matching_files = glob.glob(search_pattern)
        
        if matching_files:
            audio_path = matching_files[0]
            logger.info(f"[TIMING] [REQ:{request_id}] Found audio file: {audio_path}")
            return send_range_file(audio_path, request_id)
            
        # If no match found, try with URL-decoded version
        decoded_name = unquote(base_name)
        logger.info(f"[TIMING] [REQ:{request_id}] Trying decoded name: {decoded_name}")
        
        search_pattern = os.path.join(audio_dir, '*', f"{decoded_name}.opus")
        matching_files = glob.glob(search_pattern)
        
        if matching_files:
            audio_path = matching_files[0]
            logger.info(f"[TIMING] [REQ:{request_id}] Found audio file after decoding: {audio_path}")
            return send_range_file(audio_path, request_id)
            
        logger.error(f"[TIMING] [REQ:{request_id}] Audio file not found for: {filename}")
        return f"Audio file not found for {filename}", 404
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"[TIMING] [REQ:{request_id}] Error serving audio file {filename}: {str(e)} after {duration_ms:.2f}ms")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", 404

@bp.route('/check-audio/<filename>')
@login_required
def check_audio(filename):
    try:
        audio_dir = current_app.config.get('AUDIO_DIR')
        if not audio_dir:
            return "AUDIO_DIR not configured", 500
            
        base_name = filename.rsplit('.', 1)[0]
        search_pattern = os.path.join(audio_dir, '*', f"{base_name}.opus")
        matching_files = glob.glob(search_pattern)
        
        if matching_files:
            audio_path = matching_files[0]
            return f"File exists! Size: {os.path.getsize(audio_path)} bytes"
            
        return "File not found!", 404
    except Exception as e:
        return f"Error: {str(e)}", 500 