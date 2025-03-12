#!/usr/bin/env python
import os
import sys
import argparse
from run import initialize_app, initialize_file_service, initialize_search_index

# Define a function to parse arguments and initialize the app
def create_app(data_dir='data', force_reindex=False):
    # Initialize app with custom data directory
    app = initialize_app(data_dir)
    
    # Initialize services within app context
    with app.app_context():
        # Initialize file service
        file_service = initialize_file_service(app)
        
        # Build search index
        search_service = initialize_search_index(file_service, force_rebuild=force_reindex)
        
        # Store services in app config for access in routes
        app.config['FILE_SERVICE'] = file_service
        app.config['SEARCH_SERVICE'] = search_service
        
        # Also store in main.py module for direct access
        from app.routes import main
        main.file_service = file_service
        main.search_service = search_service
    
    return app

# When imported by Gunicorn, use default values
application = create_app()

# When run directly, parse command line arguments
if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='WSGI entry point for ivrit.ai Explore application')
    parser.add_argument('--data-dir', type=str, help='Path to the data directory', default='data')
    parser.add_argument('--force-reindex', action='store_true', help='Force rebuilding of search indices')
    parser.add_argument('--port', type=int, help='Port to run the server on', default=8000)
    args = parser.parse_args()
    
    # Create app with parsed arguments
    app = create_app(data_dir=args.data_dir, force_reindex=args.force_reindex)
    
    # Run the Flask development server
    app.run(host='0.0.0.0', port=args.port) 