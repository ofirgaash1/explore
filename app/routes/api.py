from flask import Blueprint, request, jsonify, current_app
import logging
import time
import uuid

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/log-timing', methods=['POST'])
def log_timing():
    """Endpoint to receive time logging data from client-side"""
    try:
        data = request.json
        
        if not data or 'event_type' not in data:
            return jsonify({'error': 'Invalid data format'}), 400
            
        event_type = data.get('event_type')
        event_data = data.get('data', {})
        duration_ms = event_data.get('duration_ms')
        request_id = event_data.get('request_id', str(uuid.uuid4())[:8])
        
        # Log the event
        if duration_ms:
            logger.info(f"[TIMING] [REQ:{request_id}] [CLIENT] {event_type}: {duration_ms:.2f}ms - {event_data}")
        else:
            logger.info(f"[TIMING] [REQ:{request_id}] [CLIENT] {event_type}: {event_data}")
        
        # Simple response to minimize bandwidth
        return '', 204
        
    except Exception as e:
        logger.error(f"Error processing timing log: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 