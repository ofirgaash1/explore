from .cache_service import load_json_file
import re
import logging
import time
import os

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, file_service):
        self.file_service = file_service
        self.all_segments = {}  # Dictionary to store all segments by source
        self.index_built = False
    
    def build_search_index(self, force_rebuild=False):
        """Load all segments into memory for fast searching"""
        if self.index_built and not force_rebuild:
            logger.info("Search index already built, skipping")
            return
            
        start_time = time.time()
        logger.info("Building simple search index...")
        
        available_files = self.file_service.get_available_files()
        total_segments = 0
        
        # Load all segments from all files
        for source, file_info in available_files.items():
            file_start = time.time()
            logger.info(f"Loading segments from: {source}")
            
            segments = self._get_segments(file_info['json_path'], source)
            self.all_segments[source] = segments
            
            segment_count = len(segments)
            total_segments += segment_count
            
            file_time = time.time() - file_start
            logger.info(f"Loaded {segment_count} segments from {source} in {file_time:.2f} seconds")
        
        self.index_built = True
        total_time = time.time() - start_time
        logger.info(f"Search index built in {total_time:.2f} seconds")
        logger.info(f"Total segments loaded: {total_segments}")
    
    def search(self, query, use_regex=False, use_substring=False, max_results=100):
        """Search all segments for the query with a limit on results"""
        start_time = time.time()
        
        # Build index if not already built
        if not self.index_built:
            logger.info("Index not built yet, building now...")
            self.build_search_index()
        
        logger.info(f"Searching for: '{query}' (regex: {use_regex}, substring: {use_substring}, max_results: {max_results})")
        
        # Determine search strategy
        if use_regex:
            logger.info("Using regex search strategy")
            results = self._regex_search(query, max_results)
        elif use_substring:
            logger.info("Using substring search strategy")
            results = self._substring_search(query, max_results)
        else:
            logger.info("Using full word search strategy")
            results = self._full_word_search(query, max_results)
        
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time*1000:.2f}ms, found {len(results)} results")
        
        if len(results) >= max_results:
            logger.info(f"Search stopped after reaching max_results limit ({max_results})")
        
        return results
    
    def _substring_search(self, query, max_results=100):
        """Simple case-insensitive substring search with result limit"""
        results = []
        query_lower = query.lower()
        
        # Track performance by source
        source_times = {}
        
        for source, segments in self.all_segments.items():
            source_start = time.time()
            source_results = 0
            
            for i, segment in enumerate(segments):
                if len(results) >= max_results:
                    logger.info(f"Reached max results ({max_results}), stopping search")
                    break
                    
                if 'text' not in segment:
                    continue
                
                if query_lower in segment['text'].lower():
                    results.append({
                        'start': segment['start'],
                        'text': segment['text'],
                        'source': source
                    })
                    source_results += 1
            
            source_time = time.time() - source_start
            source_times[source] = {
                'time': source_time,
                'results': source_results,
                'segments': len(segments)
            }
            
            if len(results) >= max_results:
                break
        
        # Log the slowest sources
        sorted_sources = sorted(source_times.items(), key=lambda x: x[1]['time'], reverse=True)
        if sorted_sources:
            logger.info("Slowest sources in search:")
            for source, stats in sorted_sources[:3]:  # Top 3 slowest
                logger.info(f"  {source}: {stats['time']:.4f}s, {stats['results']} results, {stats['segments']} segments")
        
        return results
    
    def _full_word_search(self, query, max_results=100):
        """Search for full word matches only with result limit"""
        results = []
        
        # Create a regex pattern that matches the query as a whole word
        # \b represents a word boundary
        pattern = r'\b' + re.escape(query) + r'\b'
        
        try:
            # Compile the regex pattern
            regex = re.compile(pattern, re.IGNORECASE)
            
            for source, segments in self.all_segments.items():
                for segment in segments:
                    if len(results) >= max_results:
                        logger.info(f"Reached max results ({max_results}), stopping search")
                        break
                        
                    if 'text' not in segment:
                        continue
                    
                    if regex.search(segment['text']):
                        results.append({
                            'start': segment['start'],
                            'text': segment['text'],
                            'source': source
                        })
                
                if len(results) >= max_results:
                    break
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            # Fall back to substring search if regex fails
            return self._substring_search(query, max_results)
        
        return results
    
    def _regex_search(self, pattern, max_results=100):
        """Search using regex pattern matching with result limit"""
        results = []
        
        try:
            # Compile the regex pattern
            regex = re.compile(pattern, re.IGNORECASE)
            
            for source, segments in self.all_segments.items():
                for segment in segments:
                    if len(results) >= max_results:
                        logger.info(f"Reached max results ({max_results}), stopping search")
                        break
                        
                    if 'text' not in segment:
                        continue
                    
                    if regex.search(segment['text']):
                        results.append({
                            'start': segment['start'],
                            'text': segment['text'],
                            'source': source
                        })
                
                if len(results) >= max_results:
                    break
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            # Fall back to literal search if regex is invalid
            return self._substring_search(pattern, max_results)
        
        return results
    
    def _full_scan_search(self, query, max_results=100):
        """Legacy method for compatibility - now just calls substring search"""
        return self._substring_search(query, max_results)
    
    def search_segments(self, query, source_file, available_files, use_substring=False, max_results=100):
        """Search segments in a specific source file with result limit"""
        # If we have the segments already loaded, use them
        if self.index_built and source_file in self.all_segments:
            results = []
            
            if use_substring:
                # Substring search
                query_lower = query.lower()
                for segment in self.all_segments[source_file]:
                    if len(results) >= max_results:
                        break
                        
                    try:
                        if 'text' not in segment:
                            continue
                        
                        if query_lower in segment['text'].lower():
                            results.append({
                                'start': segment['start'],
                                'text': segment['text'],
                                'source': source_file
                            })
                    except Exception as e:
                        logger.error(f"Error processing segment in {source_file}: {e}")
                        continue
            else:
                # Full word search
                pattern = r'\b' + re.escape(query) + r'\b'
                try:
                    regex = re.compile(pattern, re.IGNORECASE)
                    for segment in self.all_segments[source_file]:
                        if len(results) >= max_results:
                            break
                            
                        if 'text' not in segment:
                            continue
                        
                        if regex.search(segment['text']):
                            results.append({
                                'start': segment['start'],
                                'text': segment['text'],
                                'source': source_file
                            })
                except re.error:
                    # Fall back to substring search if regex fails
                    return self.search_segments(query, source_file, available_files, use_substring=True, max_results=max_results)
            
            return results
        
        # Otherwise, load from file
        file_info = available_files[source_file]
        segments = self._get_segments(file_info['json_path'], source_file)
        
        results = []
        
        if use_substring:
            # Substring search
            query_lower = query.lower()
            for segment in segments:
                if len(results) >= max_results:
                    break
                    
                try:
                    if 'text' not in segment:
                        continue
                    
                    if query_lower in segment['text'].lower():
                        results.append({
                            'start': segment['start'],
                            'text': segment['text'],
                            'source': source_file
                        })
                except Exception as e:
                    logger.error(f"Error processing segment in {source_file}: {e}")
                    continue
        else:
            # Full word search
            pattern = r'\b' + re.escape(query) + r'\b'
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for segment in segments:
                    if len(results) >= max_results:
                        break
                        
                    if 'text' not in segment:
                        continue
                    
                    if regex.search(segment['text']):
                        results.append({
                            'start': segment['start'],
                            'text': segment['text'],
                            'source': source_file
                        })
            except re.error:
                # Fall back to substring search if regex fails
                return self.search_segments(query, source_file, available_files, use_substring=True, max_results=max_results)
        
        return results
    
    def _get_segments(self, json_path, source):
        """Load segments from a JSON file"""
        data = load_json_file(json_path)
        if data and 'segments' in data:
            return data['segments']
        return []