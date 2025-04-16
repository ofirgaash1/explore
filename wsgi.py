#!/usr/bin/env python
import os
import sys
import argparse
from run import app, initialize_app, initialize_file_service, initialize_search_index

# When run directly, parse command line arguments
if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the ivrit.ai Explore application')
    parser.add_argument('--data-dir', type=str, help='Path to the data directory', default='/root/data')
    args = parser.parse_args()
    
    # Run the Flask development server
    app.run(host='0.0.0.0')
else:
    # When run through uwsgi, get arguments from sys.argv
    # This will handle the --pyargv option from uwsgi
    parser = argparse.ArgumentParser(description='Run the ivrit.ai Explore application')
    parser.add_argument('--data-dir', type=str, help='Path to the data directory', default='/root/data')
    args, unknown = parser.parse_known_args()
    
    # Set the data directory in app config
    app.config['DATA_DIR'] = os.path.abspath(args.data_dir) 