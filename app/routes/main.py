from flask import Blueprint, render_template, request, jsonify, current_app
from ..services.search_service import SearchService
from ..services.file_service import FileService
# from pydub import AudioSegment  # Commented out
import time
import os

bp = Blueprint('main', __name__)

# Global search service instance for persistence
search_service = None

@bp.route('/')
def home():
    # Initialize search index on first request
    global search_service
    if search_service is None:
        file_service = FileService(current_app)
        search_service = SearchService(file_service)
        # Build the index in the background
        search_service.build_search_index()
    
    return render_template('home.html')

@bp.route('/search')
def search():
    query = request.args.get('q', '')
    
    start_time = time.time()
    
    # Use the global search service
    global search_service
    if search_service is None:
        file_service = FileService(current_app)
        search_service = SearchService(file_service)
        search_service.build_search_index()
    
    # Perform the search
    results = search_service.search(query)
    
    # Get available files for audio paths
    file_service = FileService(current_app)
    available_files = file_service.get_available_files()
    
    # Calculate audio durations - commented out due to ffmpeg dependency issues
    audio_durations = {}
    total_audio_duration = 0
    
    '''
    # This section is commented out due to ffmpeg dependency issues
    for source, file_info in available_files.items():
        try:
            # Get audio file length from metadata if possible
            audio_path = file_info['audio_path']
            if os.path.exists(audio_path):
                audio = AudioSegment.from_file(audio_path, format=file_info['audio_format'])
                duration_minutes = len(audio) / 60000  # Convert ms to minutes
                audio_durations[source] = duration_minutes
                total_audio_duration += duration_minutes
        except Exception as e:
            print(f"Error getting duration for {source}: {e}")
    '''
    
    search_duration = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'results': results,
            'stats': {
                'count': len(results),
                'duration_ms': search_duration,
                'total_audio_minutes': total_audio_duration
            }
        })
        
    return render_template('results.html', 
                         query=query,
                         results=results,
                         available_files=available_files,
                         search_duration=search_duration,
                         audio_durations=audio_durations,
                         total_audio_duration=total_audio_duration) 