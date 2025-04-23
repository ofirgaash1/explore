from flask import Flask
from pathlib import Path
from .services.analytics_service import AnalyticsService
import os
from dotenv import load_dotenv, dotenv_values 
from flask_oauthlib.client import OAuth

load_dotenv() 

def create_app():
    app = Flask(__name__)
    
    # Configure base paths
    app.config['BASE_DIR'] = Path(__file__).parent.parent
    app.config['JSON_DIR'] = app.config['BASE_DIR'] / "data" / "json"
    app.config['AUDIO_DIR'] = app.config['BASE_DIR'] / "data" / "audio"
    
    # Ensure directories exist
    app.config['JSON_DIR'].mkdir(parents=True, exist_ok=True)
    app.config['AUDIO_DIR'].mkdir(parents=True, exist_ok=True)
    
    # Configure PostHog
    
    app.config['POSTHOG_API_KEY'] = os.environ.get('POSTHOG_API_KEY', '')
    app.config['POSTHOG_HOST'] = os.environ.get('POSTHOG_HOST', 'https://app.posthog.com')
    app.config['DISABLE_ANALYTICS'] = os.environ.get('DISABLE_ANALYTICS', '').lower() in ('true', '1', 'yes')
    
    # Initialize analytics service
    analytics_service = AnalyticsService(
        api_key=app.config['POSTHOG_API_KEY'],
        host=app.config['POSTHOG_HOST'],
        disabled=app.config['DISABLE_ANALYTICS']
    )
    app.config['ANALYTICS_SERVICE'] = analytics_service
    
    app.config['MIME_TYPES'] = {'opus': 'audio/opus'}
    
    # Set secret key for session
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Initialize Google OAuth
    from .routes.auth import init_oauth, bp as auth_bp
    google = init_oauth(app)
    app.extensions['google_oauth'] = google
    
    # Register blueprints
    from .routes import main, audio, export, api
    app.register_blueprint(main.bp)
    app.register_blueprint(audio.bp)
    app.register_blueprint(export.bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api.bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app

def register_error_handlers(app):
    @app.errorhandler(404)
    def handle_not_found(e):
        analytics = app.config.get('ANALYTICS_SERVICE')
        if analytics:
            analytics.capture_error('not_found', str(e))
        return 'Page not found', 404
        
    @app.errorhandler(500)
    def handle_server_error(e):
        analytics = app.config.get('ANALYTICS_SERVICE')
        if analytics:
            analytics.capture_error('server_error', str(e))
        return 'Internal server error', 500 