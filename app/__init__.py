from flask import Flask
from pathlib import Path
from .services.analytics_service import AnalyticsService
import os

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
    posthog_api_key = os.environ.get('POSTHOG_API_KEY', '')
    posthog_host = os.environ.get('POSTHOG_HOST', 'https://app.posthog.com')
    analytics_disabled = os.environ.get('DISABLE_ANALYTICS', '').lower() in ('true', '1', 'yes')
    
    # Initialize analytics service
    analytics_service = AnalyticsService(
        api_key=posthog_api_key,
        host=posthog_host,
        disabled=analytics_disabled or not posthog_api_key
    )
    app.config['ANALYTICS_SERVICE'] = analytics_service
    
    app.config['MIME_TYPES'] = {'opus': 'audio/opus'}
    
    # Register blueprints
    from .routes import main, audio, export
    app.register_blueprint(main.bp)
    app.register_blueprint(audio.bp)
    app.register_blueprint(export.bp)
    
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