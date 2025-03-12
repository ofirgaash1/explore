#!/usr/bin/env python
import os
import sys
import argparse
from run import initialize_app, initialize_file_service, initialize_search_index

# Parse command line arguments
parser = argparse.ArgumentParser(description='WSGI entry point for ivrit.ai Explore application')
parser.add_argument('--data-dir', type=str, help='Path to the data directory', default='data')
parser.add_argument('--force-reindex', action='store_true', help='Force rebuilding of search indices')
args = parser.parse_args()

# Initialize app with custom data directory
app = initialize_app(args.data_dir)

# Initialize services within app context
with app.app_context():
    # Initialize file service
    file_service = initialize_file_service(app)
    
    # Build search index
    search_service = initialize_search_index(file_service, force_rebuild=args.force_reindex)
    
    # Store services in app config for access in routes
    app.config['FILE_SERVICE'] = file_service
    app.config['SEARCH_SERVICE'] = search_service
    
    # Also store in main.py module for direct access
    from app.routes import main
    main.file_service = file_service
    main.search_service = search_service

# This is the WSGI application object that WSGI servers will use
application = app

# For running with the Flask development server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 