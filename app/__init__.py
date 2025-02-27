from flask import Flask
from pathlib import Path

def create_app():
    app = Flask(__name__)
    
    # Configure base paths
    app.config['BASE_DIR'] = Path(__file__).parent.parent
    app.config['JSON_DIR'] = app.config['BASE_DIR'] / "data" / "json"
    app.config['AUDIO_DIR'] = app.config['BASE_DIR'] / "data" / "audio"
    
    # Ensure directories exist
    app.config['JSON_DIR'].mkdir(parents=True, exist_ok=True)
    app.config['AUDIO_DIR'].mkdir(parents=True, exist_ok=True)
    
    # Register blueprints
    from .routes import main, audio, export
    app.register_blueprint(main.bp)
    app.register_blueprint(audio.bp)
    app.register_blueprint(export.bp)
    
    return app 