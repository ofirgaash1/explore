from flask import Blueprint, send_file, current_app, request, Response
from urllib.parse import unquote
from ..services.file_service import FileService
from ..routes.auth import login_required
import os
import mimetypes
import re
import time
import logging
import uuid

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

        with open(path, 'rb') as f:
            f.seek(byte1)
            data = f.read(length)

        resp = Response(data, 206, mimetype=content_type)
        resp.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
        resp.headers.add('Accept-Ranges', 'bytes')
        resp.headers.add('Content-Length', str(length))
        
        if request_id:
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"[TIMING] [REQ:{request_id}] Range file served in {duration_ms:.2f}ms")
        
        return resp

    # No Range: return full file
    if request_id:
        logger.info(f"[TIMING] [REQ:{request_id}] Serving full file: {size} bytes")
        
    with open(path, 'rb') as f:
        data = f.read()

    resp = Response(data, 200, mimetype=content_type)
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
        
        file_service = FileService(current_app)
        available_files = file_service.get_available_files()
        
        # Try to find an exact match first
        if base_name in available_files:
            file_info = available_files[base_name]
            logger.info(f"[TIMING] [REQ:{request_id}] Found exact match: {file_info['audio_path']}")
            return send_range_file(file_info['audio_path'], request_id)
            
        # If no exact match, try URL-decoded version
        decoded_name = unquote(base_name)
        logger.info(f"[TIMING] [REQ:{request_id}] Trying decoded name: {decoded_name}")
        
        if decoded_name in available_files:
            file_info = available_files[decoded_name]
            logger.info(f"[TIMING] [REQ:{request_id}] Found match after decoding: {file_info['audio_path']}")
            return send_range_file(file_info['audio_path'], request_id)
            
        logger.error(f"[TIMING] [REQ:{request_id}] Audio file not found. Available files: {list(available_files.keys())}")
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
        file_service = FileService(current_app)
        available_files = file_service.get_available_files()
        
        base_name = filename.rsplit('.', 1)[0]
        if base_name in available_files:
            file_info = available_files[base_name]
            return f"File exists! Size: {os.path.getsize(file_info['audio_path'])} bytes"
            
        return "File not found!", 404
    except Exception as e:
        return f"Error: {str(e)}", 500 