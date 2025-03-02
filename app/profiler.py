import cProfile
import pstats
import io
from pstats import SortKey
import time
import sys
import os
import logging
import argparse

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.services.file_service import FileService
from app.services.search_service import SearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def profile_full_scan_search(query, num_runs=1, detailed=False):
    """Profile the full scan search with a specific query"""
    logger.info(f"Profiling full_scan_search with query: '{query}'")
    
    # Initialize app and services
    app = create_app()
    
    with app.app_context():
        file_service = FileService(app)
        search_service = SearchService(file_service)
        
        # First, measure total execution time
        start_time = time.time()
        for _ in range(num_runs):
            results = search_service._full_scan_search(query)
        total_time = time.time() - start_time
        
        logger.info(f"Found {len(results)} results in {total_time:.2f} seconds (avg: {total_time/num_runs:.2f}s per run)")
        
        # Now profile with cProfile
        pr = cProfile.Profile()
        pr.enable()
        
        results = search_service._full_scan_search(query)
        
        pr.disable()
        
        # Print results to console
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(20)  # Print top 20 functions by cumulative time
        logger.info(s.getvalue())
        
        # Also save detailed results to file
        with open('profile_results.txt', 'w') as f:
            ps = pstats.Stats(pr, stream=f).sort_stats(SortKey.CUMULATIVE)
            ps.print_stats()
            
            # Print callers of the slowest functions
            f.write("\n\nCallers of the slowest functions:\n")
            ps.print_callers(20)
            
            # Print callees of the slowest functions
            f.write("\n\nFunctions called by the slowest functions:\n")
            ps.print_callees(20)
            
            # If detailed profiling is requested, also profile by file
            if detailed:
                f.write("\n\nDetailed profiling by file:\n")
                available_files = file_service.get_available_files()
                
                for source in available_files:
                    f.write(f"\n\nProfiling file: {source}\n")
                    file_pr = cProfile.Profile()
                    file_pr.enable()
                    
                    search_service._search_segments(query, source, available_files)
                    
                    file_pr.disable()
                    file_ps = pstats.Stats(file_pr, stream=f).sort_stats(SortKey.CUMULATIVE)
                    file_ps.print_stats(10)
        
        logger.info(f"Detailed profile results saved to profile_results.txt")
        
        return results

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Profile the full scan search')
    parser.add_argument('query', nargs='?', default="שלום", help='Search query to profile')
    parser.add_argument('--runs', type=int, default=1, help='Number of runs to average')
    parser.add_argument('--detailed', action='store_true', help='Enable detailed profiling by file')
    
    args = parser.parse_args()
    
    # Run the profiler
    profile_full_scan_search(args.query, num_runs=args.runs, detailed=args.detailed) 