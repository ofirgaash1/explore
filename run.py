from app import create_app
from app.services.file_service import FileService
from app.services.search_service import SearchService
import time
import logging
import sys
import argparse
import os

# Parse command line arguments
parser = argparse.ArgumentParser(description='Run the ivrit.ai Explore application')
parser.add_argument('--force-reindex', action='store_true', help='Force rebuilding of search indices')
parser.add_argument('--data-dir', type=str, help='Path to the data directory', default='data')
args = parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def log_timing(func):
    """Decorator to log function execution time"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting {func.__name__}...")
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"Completed {func.__name__} in {elapsed:.2f} seconds")
        return result
    return wrapper

@log_timing
def initialize_app(data_dir):
    """Initialize the Flask application with custom data directory"""
    app = create_app()
    # Set the data directory in the app config
    app.config['DATA_DIR'] = os.path.abspath(data_dir)
    logger.info(f"Using data directory: {app.config['DATA_DIR']}")
    return app

@log_timing
def initialize_file_service(app):
    """Initialize the file service and scan available files"""
    file_service = FileService(app)
    file_count = len(file_service.get_available_files())
    logger.info(f"Found {file_count} available files")
    return file_service

@log_timing
def initialize_search_index(file_service, force_rebuild=False):
    """Build the search index"""
    search_service = SearchService(file_service)
    search_service.build_search_index(force_rebuild=force_rebuild)
    return search_service

# Main execution
logger.info("=" * 50)
logger.info("Starting ivrit.ai Explore...")
logger.info("=" * 50)

if args.force_reindex:
    logger.info("Force reindex flag is set - will rebuild search indices")

logger.info(f"Using data directory: {args.data_dir}")

start_total = time.time()

# Initialize app with custom data directory
app = initialize_app(args.data_dir)

# Initialize services within app context
with app.app_context():
    logger.info("Initializing services...")
    
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
    
    # Log memory usage if psutil is available
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
    except ImportError:
        logger.info("Install psutil package to monitor memory usage")

total_time = time.time() - start_total
logger.info(f"Total initialization completed in {total_time:.2f} seconds")
logger.info("=" * 50)
logger.info("Search index is ready. Queries should be much faster now.")
logger.info("=" * 50)

if __name__ == '__main__':
    logger.info("Starting web server...")
    app.run(debug=True, port=80, host='0.0.0.0') 