from .cache_service import load_json_file
import re
from collections import defaultdict

class SearchService:
    def __init__(self, file_service):
        self.file_service = file_service
        self.word_index = {}           # Word-level inverted index
        self.n_gram_index = {}         # Character n-gram index for substring search
        self.segments_by_source = {}   # All segments stored by source
        self.index_built = False
    
    def build_search_index(self):
        """Build multiple search indices for different query types"""
        print("Building search indices...")
        available_files = self.file_service.get_available_files()
        
        # Word-level inverted index
        word_index = defaultdict(list)
        # Character n-gram index (for substring matching)
        n_gram_index = defaultdict(list)
        segments_by_source = {}
        
        # Process each source file
        for source, file_info in available_files.items():
            print(f"Indexing {source}...")
            segments = self._get_segments(file_info['json_path'], source)
            segments_by_source[source] = segments
            
            # Index each segment
            for i, segment in enumerate(segments):
                if 'text' not in segment:
                    continue
                    
                text = segment['text'].lower()
                
                # 1. Extract words for the word index
                words = re.findall(r'\b\w+\b', text)
                for word in words:
                    word_index[word].append((source, i))
                
                # 2. Create character n-grams (3-grams) for substring search
                if len(text) >= 3:
                    for j in range(len(text) - 2):
                        trigram = text[j:j+3]
                        n_gram_index[trigram].append((source, i))
        
        self.word_index = word_index
        self.n_gram_index = n_gram_index
        self.segments_by_source = segments_by_source
        self.index_built = True
        print(f"Search indices built with {len(word_index)} unique terms and {len(n_gram_index)} trigrams")
        
    def search(self, query, use_regex=False):
        """Multi-strategy search with support for regex"""
        # Build index if not already built
        if not self.index_built:
            self.build_search_index()
            
        query = query.lower()
        
        # Check for regex special characters
        has_regex_chars = any(c in query for c in r'.^$*+?()[{\|')
        
        # Determine search strategy
        if use_regex or has_regex_chars:
            return self._regex_search(query)
        elif ' ' in query:
            return self._multi_word_search(query)
        elif len(query) < 3:
            return self._full_scan_search(query)
        else:
            return self._optimized_search(query)
    
    def _optimized_search(self, query):
        """Optimized search using both word and n-gram indices"""
        results = set()  # Use a set to eliminate duplicates
        
        # 1. Check exact word matches
        if query in self.word_index:
            for source, segment_idx in self.word_index[query]:
                results.add((source, segment_idx))
        
        # 2. Check word prefix matches (if query is a word start)
        for word in self.word_index:
            if word.startswith(query) and word != query:
                for source, segment_idx in self.word_index[word]:
                    results.add((source, segment_idx))
        
        # 3. Check trigram-based substring matches (if query length >= 3)
        if len(query) >= 3:
            # Find segments containing all trigrams from the query
            trigram_candidates = set()
            first_trigram = True
            
            # Create trigrams from the query
            for i in range(len(query) - 2):
                trigram = query[i:i+3]
                
                if trigram in self.n_gram_index:
                    # For first trigram, initialize candidates
                    if first_trigram:
                        trigram_candidates = set(self.n_gram_index[trigram])
                        first_trigram = False
                    # For subsequent trigrams, keep only common candidates
                    else:
                        trigram_candidates &= set(self.n_gram_index[trigram])
                        
                    # If no common candidates left, stop searching
                    if not trigram_candidates:
                        break
            
            # Add candidates to results (may need verification for actual substring match)
            for source, segment_idx in trigram_candidates:
                segment = self.segments_by_source[source][segment_idx]
                if query in segment['text'].lower():
                    results.add((source, segment_idx))
        
        # Convert results to the expected format
        formatted_results = []
        for source, segment_idx in results:
            segment = self.segments_by_source[source][segment_idx]
            formatted_results.append({
                'start': segment['start'],
                'text': segment['text'],
                'source': source
            })
            
        return formatted_results
    
    def _multi_word_search(self, query):
        """Search for multiple words with AND logic"""
        words = query.lower().split()
        if not words:
            return []
            
        # Find segments containing all query words
        result_sets = []
        for word in words:
            # Skip very short words
            if len(word) < 2:
                continue
                
            # Get matching segments for this word
            word_matches = set()
            
            # Check exact word matches
            if word in self.word_index:
                word_matches.update(self.word_index[word])
            
            # Check prefix matches
            for indexed_word in self.word_index:
                if indexed_word.startswith(word) and indexed_word != word:
                    word_matches.update(self.word_index[indexed_word])
            
            # If any word returns no matches, we'll have no results
            if not word_matches:
                # Try a full scan for this word before giving up
                scan_results = self._full_scan_search(word)
                if not scan_results:
                    return []
                    
                # Convert scan results to (source, segment_idx) format
                for result in scan_results:
                    source = result['source']
                    segment_text = result['text']
                    # Find the segment index
                    for i, segment in enumerate(self.segments_by_source[source]):
                        if segment.get('text') == segment_text:
                            word_matches.add((source, i))
                            break
            
            result_sets.append(word_matches)
        
        # Find the intersection of all word matches
        if not result_sets:
            return []
            
        common_results = result_sets[0]
        for result_set in result_sets[1:]:
            common_results &= result_set
            
        # Convert results to the expected format
        formatted_results = []
        for source, segment_idx in common_results:
            segment = self.segments_by_source[source][segment_idx]
            formatted_results.append({
                'start': segment['start'],
                'text': segment['text'],
                'source': source
            })
            
        return formatted_results
    
    def _regex_search(self, pattern):
        """Search using regex pattern matching"""
        results = []
        
        try:
            # Compile the regex pattern
            regex = re.compile(pattern, re.IGNORECASE)
            
            # Search through all segments
            for source, segments in self.segments_by_source.items():
                for segment in segments:
                    if 'text' not in segment:
                        continue
                        
                    if regex.search(segment['text']):
                        results.append({
                            'start': segment['start'],
                            'text': segment['text'],
                            'source': source
                        })
        except re.error as e:
            print(f"Invalid regex pattern: {e}")
            # Fall back to literal search if regex is invalid
            return self._full_scan_search(pattern)
            
        return results
    
    def _full_scan_search(self, query):
        """Fall back to full scan for complex queries or short terms"""
        available_files = self.file_service.get_available_files()
        all_results = []
        
        for source in available_files:
            results = self.search_segments(query, source, available_files)
            all_results.extend(results)
            
        return all_results
    
    def search_segments(self, query, source_file, available_files):
        results = []
        file_info = available_files[source_file]
        
        segments = self._get_segments(file_info['json_path'], source_file)
        for segment in segments:
            try:
                if query.lower() in str(segment['text']).lower():
                    results.append({
                        'start': segment['start'],
                        'text': segment['text'],
                        'source': source_file
                    })
            except Exception as e:
                print(f"Error processing segment in {source_file}: {e}")
                continue
        
        return results
    
    def _get_segments(self, json_path, source):
        data = load_json_file(json_path)
        if data and 'segments' in data:
            return data['segments']
        return []