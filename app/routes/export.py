from flask import Blueprint, request, send_file, current_app, jsonify
import io
import csv
from pydub import AudioSegment
from ..services.file_service import FileService
from ..services.search_service import SearchService
from ..services.analytics_service import track_performance
import logging
import time

logger = logging.getLogger(__name__)

bp = Blueprint('export', __name__)

@bp.route('/export/results/<query>')
@track_performance('export_csv', include_args=['query'])
def export_results_csv(query):
    # Get the same parameters as the search route
    use_regex = request.args.get('regex', '').lower() in ('true', 'on', '1', 'yes')
    use_substring = request.args.get('substring', '').lower() in ('true', 'on', '1', 'yes')
    
    start_time = time.time()
    
    # Get search service from main module
    from ..routes import main
    search_service = main.search_service
    
    # Check if we already have results for this query
    search_key = f"{query}_{use_regex}_{use_substring}"
    
    if search_service.last_search_results.get('key') == search_key:
        # Use the cached results - this is the optimization
        logger.info(f"Using cached search results for CSV export: {query}")
        all_results = search_service.last_search_results['results']
    else:
        # If no cached results, perform a new search to get all results
        logger.info(f"No cached results found, performing new search for CSV export: {query}")
        # Use a very large max_results instead of None to avoid the pagination issue
        search_result = search_service.search(
            query, 
            use_regex=use_regex, 
            use_substring=use_substring, 
            max_results=1000000,  # Very large number instead of None
            page=1
        )
        all_results = search_result['results']
    
    # Create CSV in memory with UTF-8 BOM for Excel compatibility
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM
    writer = csv.writer(output, dialect='excel')
    writer.writerow(['Source', 'Text', 'Start Time', 'End Time'])
    
    for r in all_results:
        text = r['text'].encode('utf-8', errors='replace').decode('utf-8')
        writer.writerow([r['source'], text, r['start'], r.get('end', '')])
    
    execution_time = (time.time() - start_time) * 1000
    
    # Track export analytics
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_export(
            export_type='csv',
            query=query,
            execution_time_ms=execution_time
        )
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv; charset=utf-8',
        as_attachment=True,
        download_name=f'search_results_{query}.csv'
    )

@bp.route('/export/source/<source>')
def export_source_files(source):
    file_service = FileService(current_app)
    available_files = file_service.get_available_files()
    
    if source not in available_files:
        return "Source not found", 404
        
    file_info = available_files[source]
    file_type = request.args.get('type', 'json')
    
    if file_type == 'json':
        return send_file(
            file_info['json_path'],
            mimetype='application/json',
            as_attachment=True,
            download_name=f'{source}.json'
        )
    elif file_type == 'audio':
        return send_file(
            file_info['audio_path'],
            mimetype=f'audio/{file_info["audio_format"]}',
            as_attachment=True,
            download_name=f'{source}.{file_info["audio_format"]}'
        )

@bp.route('/export/segment/<source>')
def export_segment(source):
    start_time = float(request.args.get('start', 0))
    duration = float(request.args.get('duration', 10))
    
    file_service = FileService(current_app)
    available_files = file_service.get_available_files()
    
    if source not in available_files:
        return "Source not found", 404
    
    try:
        file_info = available_files[source]
        audio_path = file_info['audio_path']
        audio_format = file_info['audio_format']
        
        if not AudioSegment.ffmpeg:
            return "Error: ffmpeg not found. Please install ffmpeg.", 500
            
        audio = AudioSegment.from_file(audio_path, format=audio_format)
        
        start_ms = int(start_time * 1000)
        duration_ms = int(duration * 1000)
        
        if start_ms >= len(audio):
            return f"Start time {start_time}s exceeds audio length {len(audio)/1000}s", 400
            
        if start_ms + duration_ms > len(audio):
            duration_ms = len(audio) - start_ms
            
        segment = audio[start_ms:start_ms + duration_ms]
        
        buffer = io.BytesIO()
        segment.export(buffer, format=audio_format)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype=f'audio/{audio_format}',
            as_attachment=True,
            download_name=f'{source}_segment_{start_time:.2f}.{audio_format}'
        )
    except Exception as e:
        print(f"Error in export_segment: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error exporting segment: {str(e)}", 500 