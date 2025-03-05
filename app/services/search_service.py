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
        self.full_texts = {}    # Dictionary to store full texts by source
        self.index_built = False
        self.last_search_results = {}  # Store complete results of last search for pagination
    
    def build_search_index(self, force_rebuild=False):
        """Load all segments into memory for fast searching, and create full texts"""
        if self.index_built and not force_rebuild:
            logger.info("Search index already built, skipping")
            return
            
        start_time = time.time()
        logger.info("Building two-phase search index...")
        
        available_files = self.file_service.get_available_files()
        total_segments = 0
        
        # Load all segments from all files
        for source, file_info in available_files.items():
            file_start = time.time()
            logger.info(f"Loading segments from: {source}")
            
            segments = self._get_segments(file_info['json_path'], source)
            self.all_segments[source] = segments
            
            # Create full text for this source by concatenating all segments
            full_text = " ".join([segment.get('text', '') for segment in segments])
            self.full_texts[source] = full_text
            
            segment_count = len(segments)
            total_segments += segment_count
            
            file_time = time.time() - file_start
            logger.info(f"Loaded {segment_count} segments from {source} in {file_time:.2f} seconds")
        
        self.index_built = True
        total_time = time.time() - start_time
        logger.info(f"Two-phase search index built in {total_time:.2f} seconds")
        logger.info(f"Total segments loaded: {total_segments}")
    
    def search(self, query, use_regex=False, use_substring=False, max_results=100, page=1):
        """
        Two-phase search with pagination:
        1. First search in full texts to identify relevant sources
        2. Then search segments only within those matching sources
        3. Return paginated results based on page number
        """
        start_time = time.time()
        
        # Build index if not already built
        if not self.index_built:
            logger.info("Index not built yet, building now...")
            self.build_search_index()
        
        # Check if we're requesting a new page of the same search
        search_key = f"{query}_{use_regex}_{use_substring}"
        is_new_search = not self.last_search_results.get('key') == search_key
        
        if is_new_search:
            logger.info(f"New search for: '{query}' (regex: {use_regex}, substring: {use_substring})")
            
            # Phase 1: Identify matching sources from full texts
            matching_sources = self._find_matching_sources(query, use_regex, use_substring)
            logger.info(f"Phase 1 complete: Found {len(matching_sources)} matching sources")
            
            # Phase 2: Search within segments of matching sources (get all results)
            if use_regex:
                logger.info("Using regex search strategy")
                all_results = self._regex_search(query, None, matching_sources)
            elif use_substring:
                logger.info("Using substring search strategy")
                all_results = self._substring_search(query, None, matching_sources)
            else:
                logger.info("Using full word search strategy")
                all_results = self._full_word_search(query, None, matching_sources)
            
            # Store all results for pagination
            self.last_search_results = {
                'key': search_key,
                'query': query,
                'results': all_results,
                'total': len(all_results)
            }
        else:
            logger.info(f"Fetching page {page} of existing search for: '{query}'")
            all_results = self.last_search_results['results']
        
        # Handle the case where we want all results (no pagination)
        if max_results is None:
            logger.info(f"Returning all {len(all_results)} results (no pagination)")
            return {
                'results': all_results,
                'pagination': {
                    'page': 1,
                    'total_pages': 1,
                    'total_results': len(all_results),
                    'per_page': len(all_results),
                    'has_next': False,
                    'has_prev': False
                }
            }
        
        # Calculate pagination
        start_idx = (page - 1) * max_results
        end_idx = start_idx + max_results
        paginated_results = all_results[start_idx:end_idx]
        
        total_results = len(all_results)
        total_pages = (total_results + max_results - 1) // max_results  # Ceiling division
        
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time*1000:.2f}ms, returning page {page} of {total_pages} ({len(paginated_results)} results)")
        
        # Return paginated results with pagination metadata
        return {
            'results': paginated_results,
            'pagination': {
                'page': page,
                'total_pages': total_pages,
                'total_results': total_results,
                'per_page': max_results,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
    
    def _find_matching_sources(self, query, use_regex=False, use_substring=False):
        """Find sources with full texts that match the query"""
        matching_sources = []
        
        if use_regex:
            try:
                regex = re.compile(query, re.IGNORECASE)
                for source, full_text in self.full_texts.items():
                    if regex.search(full_text):
                        matching_sources.append(source)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                # Fall back to substring matching
                return self._find_matching_sources(query, False, True)
        
        elif use_substring:
            query_lower = query.lower()
            for source, full_text in self.full_texts.items():
                if query_lower in full_text.lower():
                    matching_sources.append(source)
        
        else:
            # Full word search
            pattern = r'\b' + re.escape(query) + r'\b'
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for source, full_text in self.full_texts.items():
                    if regex.search(full_text):
                        matching_sources.append(source)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                # Fall back to substring matching
                return self._find_matching_sources(query, False, True)
        
        return matching_sources
    
    def _substring_search(self, query, max_results=None, matching_sources=None):
        """Simple case-insensitive substring search with optional result limit"""
        results = []
        query_lower = query.lower()
        
        # Track performance by source
        source_times = {}
        
        # If matching_sources is None, search all sources
        sources_to_search = matching_sources if matching_sources is not None else self.all_segments.keys()
        
        for source in sources_to_search:
            if source not in self.all_segments:
                continue
                
            segments = self.all_segments[source]
            source_start = time.time()
            source_results = 0
            
            for i, segment in enumerate(segments):
                if max_results is not None and len(results) >= max_results:
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
            
            if max_results is not None and len(results) >= max_results:
                break
        
        # Log the slowest sources
        sorted_sources = sorted(source_times.items(), key=lambda x: x[1]['time'], reverse=True)
        if sorted_sources:
            logger.info("Slowest sources in search:")
            for source, stats in sorted_sources[:3]:  # Top 3 slowest
                logger.info(f"  {source}: {stats['time']:.4f}s, {stats['results']} results, {stats['segments']} segments")
        
        return results
    
    def _full_word_search(self, query, max_results=None, matching_sources=None):
        """Search for full word matches only with optional result limit"""
        results = []
        
        # Create a regex pattern that matches the query as a whole word
        # \b represents a word boundary
        pattern = r'\b' + re.escape(query) + r'\b'
        
        try:
            # Compile the regex pattern
            regex = re.compile(pattern, re.IGNORECASE)
            
            # If matching_sources is None, search all sources
            sources_to_search = matching_sources if matching_sources is not None else self.all_segments.keys()
            
            for source in sources_to_search:
                if source not in self.all_segments:
                    continue
                    
                segments = self.all_segments[source]
                
                for segment in segments:
                    if max_results is not None and len(results) >= max_results:
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
                
                if max_results is not None and len(results) >= max_results:
                    break
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            # Fall back to substring search if regex fails
            return self._substring_search(query, max_results, matching_sources)
        
        return results
    
    def _regex_search(self, pattern, max_results=None, matching_sources=None):
        """Search using regex pattern matching with optional result limit"""
        results = []
        
        try:
            # Compile the regex pattern
            regex = re.compile(pattern, re.IGNORECASE)
            
            # If matching_sources is None, search all sources
            sources_to_search = matching_sources if matching_sources is not None else self.all_segments.keys()
            
            for source in sources_to_search:
                if source not in self.all_segments:
                    continue
                    
                segments = self.all_segments[source]
                
                for segment in segments:
                    if max_results is not None and len(results) >= max_results:
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
                
                if max_results is not None and len(results) >= max_results:
                    break
                    
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            # Fall back to literal search if regex is invalid
            return self._substring_search(pattern, max_results, matching_sources)
        
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