from flask import Blueprint, render_template, request, jsonify, current_app
from ..services.search_service import SearchService
from ..services.file_service import FileService
from ..services.analytics_service import track_performance
# from pydub import AudioSegment  # Commented out
from ..routes.auth import login_required
import time
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Global search service instance for persistence
search_service = None
file_service = None

@bp.route('/')
@login_required
def home():
    # Track page view
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_event('page_viewed', {'page': 'home'})
    return render_template('home.html')

@bp.route('/search')
@login_required
@track_performance('search_executed', include_args=['query', 'use_regex', 'use_substring', 'max_results', 'page'])
def search():
    query = request.args.get('q', '')
    use_regex = request.args.get('regex', '').lower() in ('true', 'on', '1', 'yes')
    use_substring = request.args.get('substring', '').lower() in ('true', 'on', '1', 'yes')
    
    # Get max_results parameter with default of 100
    try:
        max_results = int(request.args.get('max_results', 100))
        # Ensure max_results is at least 1
        max_results = max(1, max_results)
    except ValueError:
        max_results = 100
    
    # Get page parameter with default of 1
    try:
        page = int(request.args.get('page', 1))
        # Ensure page is at least 1
        page = max(1, page)
    except ValueError:
        page = 1
    
    # Enable progressive loading for first page of new searches
    progressive = page == 1 and request.args.get('progressive', '').lower() in ('true', 'on', '1', 'yes')
    
    start_time = time.time()
    
    # Use the global search service that was initialized in run.py
    global search_service, file_service
    
    # These should already be initialized in run.py, but just in case:
    if search_service is None:
        logger.info("Search service not initialized yet, initializing now...")
        if file_service is None:
            file_service = FileService(current_app)
        search_service = SearchService(file_service)
        search_service.build_search_index()
    
    # Perform the search
    logger.info(f"Searching for: '{query}' (regex: {use_regex}, substring: {use_substring}, max_results: {max_results}, page: {page}, progressive: {progressive})")
    search_result = search_service.search(
        query, 
        use_regex=use_regex, 
        use_substring=use_substring, 
        max_results=max_results,
        page=page,
        progressive=progressive
    )
    
    results = search_result['results']
    pagination = search_result['pagination']
    
    # Get available files for audio paths
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
    logger.info(f"Search completed in {search_duration:.2f}ms, found {pagination['total_results']} total results so far")
    
    # Track search analytics
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_search(
            query=query,
            use_regex=use_regex,
            use_substring=use_substring,
            max_results=max_results,
            page=page,
            execution_time_ms=search_duration,
            results_count=len(results),
            total_results=pagination['total_results'],
            progressive=progressive
        )
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'results': results,
            'pagination': pagination,
            'stats': {
                'count': len(results),
                'total_count': pagination['total_results'],
                'duration_ms': search_duration,
                'total_audio_minutes': total_audio_duration,
                'still_searching': pagination.get('still_searching', False)
            }
        })
        
    return render_template('results.html', 
                         query=query,
                         results=results,
                         pagination=pagination,
                         available_files=available_files,
                         search_duration=search_duration,
                         audio_durations=audio_durations,
                         total_audio_duration=total_audio_duration,
                         regex=use_regex,
                         substring=use_substring,
                         max_results=max_results,
                         progressive=progressive)

@bp.route('/privacy')
def privacy_policy():
    # Track page view
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_event('page_viewed', {'page': 'privacy_policy'})
    return render_template('privacy.html') 