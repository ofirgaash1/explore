from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import time
import os
from pathlib import Path

app = Flask(__name__)

# Define directories - use absolute paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
JSON_DIR = os.path.join(BASE_DIR, "data", "json")
AUDIO_DIR = os.path.join(BASE_DIR, "data", "audio")

print("Starting Flask application...")

def get_available_files():
    """Get list of JSON files and their corresponding audio files"""
    json_files = {}
    if not os.path.exists(JSON_DIR):
        print(f"Warning: {JSON_DIR} directory does not exist")
        return json_files
        
    print(f"Scanning for JSON files in: {JSON_DIR}")
    for json_path in Path(JSON_DIR).glob("*.json"):
        base_name = json_path.stem
        audio_path = Path(AUDIO_DIR) / f"{base_name}.ogg"
        print(f"Found JSON: {json_path}")
        print(f"Looking for audio: {audio_path}")
        
        if audio_path.exists():
            print(f"✓ Matching audio file found: {audio_path}")
            json_files[base_name] = {
                'json_path': str(json_path),
                'audio_path': str(audio_path)
            }
        else:
            print(f"✗ No matching audio file for {json_path}")
            
    print(f"Total available files: {len(json_files)}")
    return json_files

def load_audio_segments(json_path):
    try:
        print(f"Loading segments from {json_path}")
        
        if not os.path.exists(json_path):
            print(f"Error: {json_path} does not exist!")
            return {}
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
            
    except Exception as e:
        print(f"Error loading segments: {str(e)}")
        return {}

def search_segments(query, segments, source_file):
    results = []
    for segment_data in segments:
        try:
            if query.lower() in str(segment_data['text']).lower():
                results.append({
                    'start': segment_data['start'],
                    'text': segment_data['text'],
                    'source': source_file
                })
        except Exception as e:
            print(f"Error processing segment: {e}")
            continue
    return results

@app.route('/')
def home():
    return '''
    <html>
        <head>
            <title>Text Search</title>
        </head>
        <body>
            <h1>Search Text</h1>
            <form action="/search" method="GET">
                <input type="text" name="q" placeholder="Enter search term...">
                <button type="submit">Search</button>
            </form>
        </body>
    </html>
    '''

@app.route('/check-audio/<filename>')
def check_audio(filename):
    try:
        file_path = os.path.join(AUDIO_DIR, filename)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            return f"File exists! Size: {file_size} bytes"
        return "File not found!", 404
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/search')
def search():
    query = request.args.get('q', '')
    print(f"\nNew search request for: '{query}'")
    
    available_files = get_available_files()
    selected_files = list(available_files.keys())
    print(f"Files to search: {selected_files}")
    
    start_time = time.time()
    all_results = []
    
    for file_name in selected_files:
        file_info = available_files[file_name]
        print(f"\nProcessing file: {file_name}")
        print(f"JSON path: {file_info['json_path']}")
        print(f"Audio path: {file_info['audio_path']}")
        
        data = load_audio_segments(file_info['json_path'])
        
        if not data or 'segments' not in data:
            print(f"✗ No valid segments found in {file_name}")
            continue
            
        results = search_segments(query, data['segments'], file_name)
        print(f"Found {len(results)} matches in {file_name}")
        all_results.extend(results)
    
    search_duration = (time.time() - start_time) * 1000
    result_count = len(all_results)
    file_count = len(selected_files)
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'results': all_results,
            'stats': {
                'count': result_count,
                'file_count': file_count,
                'duration_ms': round(search_duration, 2)
            }
        })
    
    results_by_source = {}
    if all_results:
        print("\nGrouping results by source:")
        for r in all_results:
            if r['source'] not in results_by_source:
                results_by_source[r['source']] = []
            results_by_source[r['source']].append(r)
        
        # Generate HTML for each source
        results_html = ''
        for source, results in results_by_source.items():
            audio_filename = source + '.ogg'
            audio_url = f"/audio/{audio_filename}"
            
            results_html += f'''
                <div class="source-group">
                    <div class="source-header" onclick="toggleSource('{source}')">
                        <span class="toggle-icon" id="icon-{source}">▶</span>
                        <span class="source-title">{source}</span>
                        <span class="result-count">({len(results)} results)</span>
                    </div>
                    <div id="{source}-results" class="source-results" style="display: none;">
                        {''.join(f"""
                            <div class="result-item">
                                <p>{r['text']}</p>
                                <div class="audio-debug">
                                    <p>Audio URL: {audio_url}#t={r['start']}</p>
                                    <p><a href="/check-audio/{audio_filename}" target="_blank">Check audio file</a></p>
                                </div>
                                <audio controls preload="metadata">
                                    <source src="{audio_url}#t={r['start']}" type="audio/ogg">
                                    Your browser does not support the audio element.
                                </audio>
                            </div>
                        """ for r in results)}
                    </div>
                </div>
            '''
    else:
        results_html = 'No results found'
        print("No results to display")

    # Enhanced debug info
    debug_info = f'''
        <div class="debug-info" style="margin-top: 20px; padding: 10px; background: #f0f0f0; border: 1px solid #ddd;">
            <h3>Debug Info:</h3>
            <p>Base Directory: {BASE_DIR}</p>
            <p>JSON Directory: {JSON_DIR}</p>
            <p>Audio Directory: {AUDIO_DIR}</p>
            <p>Available files: {list(available_files.keys())}</p>
            <h4>Audio Files in Directory:</h4>
            <ul>
                {''.join(f"<li>{f} - {os.path.exists(os.path.join(AUDIO_DIR, f))}</li>" 
                        for f in os.listdir(AUDIO_DIR))}
            </ul>
        </div>
    '''

    return f'''
    <html>
        <head>
            <title>Search Results</title>
            <style>
                .source-group {{
                    margin: 10px 0;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                .source-header {{
                    padding: 10px;
                    background-color: #f8f8f8;
                    cursor: pointer;
                    user-select: none;
                }}
                .source-header:hover {{
                    background-color: #f0f0f0;
                }}
                .toggle-icon {{
                    display: inline-block;
                    width: 20px;
                    transition: transform 0.2s;
                }}
                .source-title {{
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .result-count {{
                    color: #666;
                }}
                .source-results {{
                    padding: 10px;
                }}
                .result-item {{
                    cursor: pointer;
                    padding: 10px;
                    border-bottom: 1px solid #eee;
                    display: flex;
                    gap: 10px;
                }}
                .result-item:hover {{
                    background-color: #f5f5f5;
                }}
                .result-item.active {{
                    background-color: #e6f3ff;
                }}
                .timestamp {{
                    color: #666;
                    min-width: 60px;
                }}
                .result-text {{
                    flex: 1;
                    margin: 0;
                }}
                .audio-player-container {{
                    position: sticky;
                    top: 0;
                    background: white;
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                    z-index: 100;
                }}
                .audio-controls {{
                    display: flex;
                    gap: 10px;
                    align-items: center;
                    margin: 10px 0;
                }}
                .audio-controls button {{
                    padding: 5px 10px;
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <h1>Search Results for: {query}</h1>
            <a href="/">Back to Search</a>
            <div class="stats">
                Found {result_count} results in {file_count} files (search took {search_duration:.2f}ms)
            </div>
            <div>
                {results_html}
            </div>
            {debug_info}
            <script>
                function toggleSource(sourceId) {{
                    const resultsDiv = document.getElementById(sourceId + '-results');
                    const icon = document.getElementById('icon-' + sourceId);
                    
                    if (resultsDiv.style.display === 'none') {{
                        resultsDiv.style.display = 'block';
                        icon.textContent = '▼';
                        icon.classList.add('rotated');
                    }} else {{
                        resultsDiv.style.display = 'none';
                        icon.textContent = '▶';
                        icon.classList.remove('rotated');
                    }}
                }}
            </script>
        </body>
    </html>
    '''

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    try:
        return send_from_directory(AUDIO_DIR, filename)
    except Exception as e:
        print(f"Error serving audio file {filename}: {str(e)}")
        return f"Error: {str(e)}", 404

if __name__ == '__main__':
    print("\nFlask server is starting...")
    print(f"Base directory: {BASE_DIR}")
    print(f"JSON directory: {JSON_DIR}")
    print(f"Audio directory: {AUDIO_DIR}")
    
    # Ensure both directories exist
    os.makedirs(JSON_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    # List contents of directories with full paths and sizes
    print("\nContents of JSON directory:")
    for f in os.listdir(JSON_DIR):
        path = os.path.join(JSON_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f} - {size} bytes")
    
    print("\nContents of Audio directory:")
    for f in os.listdir(AUDIO_DIR):
        path = os.path.join(AUDIO_DIR, f)
        size = os.path.getsize(path)
        print(f"  {f} - {size} bytes")
        
    app.run(debug=True, port=5000, host='0.0.0.0')
