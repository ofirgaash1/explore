from flask import Flask, render_template, request, jsonify
import json
import time
import os

app = Flask(__name__)

print("Starting Flask application...")

# Helper function to load and parse audio segments
def load_audio_segments():
    try:
        print(f"Current working directory: {os.getcwd()}")
        json_path = 'audio.json'
        print(f"Attempting to load audio segments from {os.path.abspath(json_path)}")
        
        if not os.path.exists(json_path):
            print(f"Error: {json_path} does not exist!")
            return {}
            
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Data type: {type(data)}")
            print(f"Keys in data: {list(data.keys())}")  # Debug print
            return data
            
    except Exception as e:
        print(f"Error loading segments: {str(e)}")
        return {}

# Search function
def search_segments(query, segments):
    results = []
    for segment_data in segments:
        try:
            # Print for debugging
            #print(f"Processing segment: {segment_data}")

            print(f"Processing segment: {segment_data['start']}, {segment_data['text']}")
            
            # Check if the query matches the text
            if query in str(segment_data['text']):
                results.append({
                    'start': segment_data['start'],
                    'text': segment_data['text']    # or the relevant part of segment_data
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

@app.route('/search')
def search():
    query = request.args.get('q', '')
    print(f"Searching for: {query}")  # Debug print
    
    start_time = time.time()
    data = load_audio_segments()
    segments = data["segments"]
    print(f"Loaded {len(segments)} segments")  # Debug print
    
    results = search_segments(query, segments)
    print(f"Found {len(results)} results")  # Debug print
    
    search_duration = (time.time() - start_time) * 1000
    result_count = len(results)
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'results': results,
            'stats': {
                'count': result_count,
                'duration_ms': round(search_duration, 2)
            }
        })
    
    results_html = ''
    if results:
        for r in results:
            results_html += f'''
                <div class="result-item">
                    <p>{r['text']}</p>
                    <audio controls>
                        <source src="/static/audio.ogg#t={r['start']}" type="audio/ogg">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            '''
    else:
        results_html = 'No results found'
    
    return f'''
    <html>
        <head>
            <title>Search Results</title>
            <style>
                .result-item {{
                    margin: 20px 0;
                    padding: 10px;
                    border: 1px solid #ddd;
                }}
                .stats {{
                    margin: 20px 0;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 4px;
                }}
                audio {{
                    width: 100%;
                    margin-top: 10px;
                }}
            </style>
        </head>
        <body>
            <h1>Search Results for: {query}</h1>
            <a href="/">Back to Search</a>
            <div class="stats">
                Found {result_count} results in {search_duration:.2f}ms
            </div>
            <div>
                {results_html}
            </div>
        </body>
    </html>
    '''

if __name__ == '__main__':
    print("Flask server is starting...")
    app.run(debug=True, port=5000, host='0.0.0.0')
