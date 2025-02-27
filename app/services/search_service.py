from .cache_service import load_json_file
import re
from collections import defaultdict

class SearchService:
    def __init__(self, file_service):
        self.file_service = file_service
        self.search_index = {}
        self.segments_by_source = {}
        self.index_built = False
    
    def build_search_index(self):
        """Build an in-memory search index for faster queries"""
        print("Building search index...")
        available_files = self.file_service.get_available_files()
        
        # Word-level inverted index
        word_index = defaultdict(list)
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
                # Extract words and remove punctuation
                words = re.findall(r'\b\w+\b', text)
                
                # Add each word to the index
                for word in words:
                    word_index[word].append((source, i))
        
        self.search_index = word_index
        self.segments_by_source = segments_by_source
        self.index_built = True
        print(f"Search index built with {len(word_index)} unique terms")
        
    def search(self, query):
        """Search using the in-memory index if available"""
        # Build index if not already built
        if not self.index_built:
            self.build_search_index()
            
        query = query.lower()
        all_results = []
        
        # Check if we should use the index or do a full scan
        if ' ' in query or len(query) < 3:
            # For multi-word queries or very short terms, do a full scan
            return self._full_scan_search(query)
        else:
            # For single word queries, use the index
            return self._indexed_search(query)
    
    def _indexed_search(self, query):
        """Search using the inverted index"""
        results = []
        
        # Find exact matches in the index
        if query in self.search_index:
            matches = self.search_index[query]
            
            # Convert index matches to result objects
            for source, segment_idx in matches:
                segment = self.segments_by_source[source][segment_idx]
                results.append({
                    'start': segment['start'],
                    'text': segment['text'],
                    'source': source
                })
        
        # Find prefix matches (for partial word search)
        for word in self.search_index:
            if word.startswith(query) and word != query:
                matches = self.search_index[word]
                for source, segment_idx in matches:
                    segment = self.segments_by_source[source][segment_idx]
                    results.append({
                        'start': segment['start'],
                        'text': segment['text'],
                        'source': source
                    })
        
        return results
    
    def _full_scan_search(self, query):
        """Fall back to full scan for complex queries"""
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