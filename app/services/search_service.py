from .cache_service import load_json_file
import re
from collections import defaultdict
import logging
import time
import json
import os
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self, file_service):
        self.file_service = file_service
        self.word_index = {}           # Word-level inverted index
        self.n_gram_index = {}         # Character n-gram index for substring search
        self.segments_by_source = {}   # All segments stored by source
        self.index_built = False
        self.index_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'index')
        
        # Create index directory if it doesn't exist
        os.makedirs(self.index_dir, exist_ok=True)
    
    def _get_index_hash(self, available_files):
        """Generate a hash of all source files to detect changes"""
        hasher = hashlib.md5()
        
        # Sort files by name for consistent hash
        for source, file_info in sorted(available_files.items()):
            file_path = file_info['json_path']
            mtime = str(os.path.getmtime(file_path))
            size = str(os.path.getsize(file_path))
            hasher.update(f"{source}:{file_path}:{mtime}:{size}".encode())
            
        return hasher.hexdigest()
    
    def _get_index_paths(self, index_hash):
        """Get paths for all index files"""
        return {
            'metadata': os.path.join(self.index_dir, f"index_metadata_{index_hash}.json"),
            'word_index': os.path.join(self.index_dir, f"word_index_{index_hash}.json"),
            'n_gram_index': os.path.join(self.index_dir, f"n_gram_index_{index_hash}.json"),
            'segments': os.path.join(self.index_dir, f"segments_{index_hash}.json")
        }
    
    def _save_indices(self, index_hash, metadata):
        """Save indices to disk"""
        start_time = time.time()
        logger.info("Saving search indices to disk...")
        
        index_paths = self._get_index_paths(index_hash)
        
        # Save metadata
        with open(index_paths['metadata'], 'w', encoding='utf-8') as f:
            json.dump(metadata, f)
        
        # Convert defaultdict to dict for serialization
        word_index_dict = {k: list(v) for k, v in self.word_index.items()}
        
        # Save word index
        with open(index_paths['word_index'], 'w', encoding='utf-8') as f:
            json.dump(word_index_dict, f)
        
        # Save n-gram index
        n_gram_index_dict = {k: list(v) for k, v in self.n_gram_index.items()}
        with open(index_paths['n_gram_index'], 'w', encoding='utf-8') as f:
            json.dump(n_gram_index_dict, f)
        
        # Save segments
        with open(index_paths['segments'], 'w', encoding='utf-8') as f:
            json.dump(self.segments_by_source, f)
        
        elapsed = time.time() - start_time
        logger.info(f"Indices saved to disk in {elapsed:.2f} seconds")
    
    def _load_indices(self, index_hash):
        """Load indices from disk"""
        start_time = time.time()
        logger.info(f"Loading search indices from disk for hash {index_hash}...")
        
        index_paths = self._get_index_paths(index_hash)
        
        # Check if all required files exist
        if not all(os.path.exists(path) for path in index_paths.values()):
            logger.info("Some index files are missing, need to rebuild")
            return False
        
        try:
            # Load word index
            with open(index_paths['word_index'], 'r', encoding='utf-8') as f:
                word_index_data = json.load(f)
                # Convert lists back to tuples for segment references
                self.word_index = {k: [(t[0], t[1]) for t in v] for k, v in word_index_data.items()}
            
            # Load n-gram index
            with open(index_paths['n_gram_index'], 'r', encoding='utf-8') as f:
                n_gram_index_data = json.load(f)
                # Convert lists back to tuples for segment references
                self.n_gram_index = {k: [(t[0], t[1]) for t in v] for k, v in n_gram_index_data.items()}
            
            # Load segments
            with open(index_paths['segments'], 'r', encoding='utf-8') as f:
                self.segments_by_source = json.load(f)
            
            self.index_built = True
            
            elapsed = time.time() - start_time
            logger.info(f"Indices loaded from disk in {elapsed:.2f} seconds")
            
            # Load and return metadata
            with open(index_paths['metadata'], 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                logger.info(f"Loaded index with {metadata['total_segments']} segments and {metadata['unique_terms']} unique terms")
                return True
                
        except Exception as e:
            logger.error(f"Error loading indices: {e}")
            return False
    
    def _clean_old_indices(self, current_hash=None):
        """Remove old index files to save disk space"""
        try:
            # Keep only the current hash and the 2 most recent other hashes
            all_index_files = [f for f in os.listdir(self.index_dir) if f.startswith("index_metadata_")]
            hash_values = set()
            
            # Extract hash values from filenames
            for filename in all_index_files:
                parts = filename.split('_')
                if len(parts) >= 3:
                    hash_value = parts[2].split('.')[0]
                    hash_values.add(hash_value)
            
            # Remove current hash from the list if provided
            if current_hash and current_hash in hash_values:
                hash_values.remove(current_hash)
            
            # Sort remaining hashes by file modification time (newest first)
            sorted_hashes = sorted(
                hash_values,
                key=lambda h: os.path.getmtime(os.path.join(self.index_dir, f"index_metadata_{h}.json")),
                reverse=True
            )
            
            # Keep only the 2 most recent hashes
            hashes_to_keep = sorted_hashes[:2]
            hashes_to_delete = [h for h in hash_values if h not in hashes_to_keep]
            
            # Delete old index files
            for hash_to_delete in hashes_to_delete:
                logger.info(f"Cleaning up old index files for hash {hash_to_delete}")
                for prefix in ['index_metadata_', 'word_index_', 'n_gram_index_', 'segments_']:
                    file_path = os.path.join(self.index_dir, f"{prefix}{hash_to_delete}.json")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        
        except Exception as e:
            logger.error(f"Error cleaning old indices: {e}")
    
    def build_search_index(self, force_rebuild=False):
        """Build multiple search indices for different query types with persistence"""
        start_time = time.time()
        logger.info("Preparing search indices...")
        available_files = self.file_service.get_available_files()
        
        # Generate a hash of the current files to detect changes
        index_hash = self._get_index_hash(available_files)
        logger.info(f"Current index hash: {index_hash}")
        
        # Try to load existing indices if not forcing rebuild
        if not force_rebuild and self._load_indices(index_hash):
            logger.info("Using existing indices from disk")
            return
        
        # If we get here, we need to build the indices
        logger.info(f"Building new search indices for {len(available_files)} files")
        
        # Word-level inverted index
        word_index = defaultdict(list)
        # Character n-gram index (for substring matching)
        n_gram_index = defaultdict(list)
        segments_by_source = {}
        
        total_segments = 0
        
        # Process each source file
        for i, (source, file_info) in enumerate(available_files.items()):
            file_start = time.time()
            logger.info(f"Indexing file {i+1}/{len(available_files)}: {source}")
            
            segments = self._get_segments(file_info['json_path'], source)
            segments_by_source[source] = segments
            total_segments += len(segments)
            
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
            
            file_time = time.time() - file_start
            logger.info(f"Indexed {len(segments)} segments from {source} in {file_time:.2f} seconds")
        
        self.word_index = word_index
        self.n_gram_index = n_gram_index
        self.segments_by_source = segments_by_source
        self.index_built = True
        
        total_time = time.time() - start_time
        
        # Prepare metadata
        metadata = {
            'created_at': time.time(),
            'build_time_seconds': total_time,
            'file_count': len(available_files),
            'total_segments': total_segments,
            'unique_terms': len(word_index),
            'trigram_count': len(n_gram_index),
            'word_index_entries': sum(len(v) for v in word_index.values())
        }
        
        # Save indices to disk
        self._save_indices(index_hash, metadata)
        
        # Clean up old indices
        self._clean_old_indices(index_hash)
        
        logger.info(f"Search indices built in {total_time:.2f} seconds:")
        logger.info(f"  - {len(word_index)} unique terms in word index")
        logger.info(f"  - {len(n_gram_index)} trigrams in n-gram index")
        logger.info(f"  - {total_segments} total segments indexed")
        logger.info(f"  - {sum(len(v) for v in word_index.values())} total word index entries")
        
    def search(self, query, use_regex=False):
        """Multi-strategy search with support for regex"""
        start_time = time.time()
        
        # Build index if not already built
        if not self.index_built:
            logger.info("Index not built yet, building now...")
            self.build_search_index()
            
        query = query.lower()
        logger.info(f"Searching for: '{query}'")
        
        # Check for regex special characters
        has_regex_chars = any(c in query for c in r'.^$*+?()[{\|')
        
        # Determine search strategy
        if use_regex or has_regex_chars:
            logger.info("Using regex search strategy")
            results = self._regex_search(query)
        elif ' ' in query:
            logger.info("Using multi-word search strategy")
            results = self._multi_word_search(query)
        elif len(query) < 3:
            logger.info("Using full scan search strategy (short query)")
            results = self._full_scan_search(query)
        else:
            logger.info("Using optimized search strategy")
            results = self._optimized_search(query)
        
        search_time = time.time() - start_time
        logger.info(f"Search completed in {search_time*1000:.2f}ms, found {len(results)} results")
        
        return results
    
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