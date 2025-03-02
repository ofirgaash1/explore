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

def profile_search(query, search_type="full_word", max_results=100, num_runs=1, detailed=False):
    """Profile the search with a specific query and search type"""
    logger.info(f"Profiling search with query: '{query}', type: {search_type}, max_results: {max_results}")
    
    # Initialize app and services
    app = create_app()
    
    with app.app_context():
        file_service = FileService(app)
        search_service = SearchService(file_service)
        
        # Build the search index first
        logger.info("Building search index...")
        search_service.build_search_index()
        
        # First, measure total execution time
        start_time = time.time()
        
        # Determine which search method to use
        use_regex = search_type == "regex"
        use_substring = search_type == "substring"
        
        for i in range(num_runs):
            logger.info(f"Run {i+1}/{num_runs}...")
            results = search_service.search(
                query, 
                use_regex=use_regex, 
                use_substring=use_substring,
                max_results=max_results
            )
            
        total_time = time.time() - start_time
        
        logger.info(f"Found {len(results)} results in {total_time:.2f} seconds (avg: {total_time/num_runs:.2f}s per run)")
        
        # Now profile with cProfile
        pr = cProfile.Profile()
        pr.enable()
        
        results = search_service.search(
            query, 
            use_regex=use_regex, 
            use_substring=use_substring,
            max_results=max_results
        )
        
        pr.disable()
        
        # Print results to console
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats(SortKey.CUMULATIVE)
        ps.print_stats(20)  # Print top 20 functions by cumulative time
        logger.info(s.getvalue())
        
        # Also save detailed results to file - using UTF-8 encoding
        with open('profile_results.txt', 'w', encoding='utf-8') as f:
            f.write(f"Profile results for search query: '{query}'\n")
            f.write(f"Search type: {search_type}\n")
            f.write(f"Max results: {max_results}\n")
            f.write(f"Number of runs: {num_runs}\n\n")
            
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
                    
                    search_service.search_segments(
                        query, 
                        source, 
                        available_files, 
                        use_substring=(search_type == "substring"),
                        max_results=max_results
                    )
                    
                    file_pr.disable()
                    file_ps = pstats.Stats(file_pr, stream=f).sort_stats(SortKey.CUMULATIVE)
                    file_ps.print_stats(10)
        
        logger.info(f"Detailed profile results saved to profile_results.txt")
        
        return results

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Profile the search functionality')
    parser.add_argument('query', nargs='?', default="שלום", help='Search query to profile')
    parser.add_argument('--type', choices=['full_word', 'substring', 'regex'], default='full_word', 
                        help='Type of search to profile')
    parser.add_argument('--max', type=int, default=100, help='Maximum number of results')
    parser.add_argument('--runs', type=int, default=1, help='Number of runs to average')
    parser.add_argument('--detailed', action='store_true', help='Enable detailed profiling by file')
    
    args = parser.parse_args()
    
    # Run the profiler
    profile_search(
        args.query, 
        search_type=args.type, 
        max_results=args.max,
        num_runs=args.runs, 
        detailed=args.detailed
    ) 