from .cache_service import load_json_file

class SearchService:
    def __init__(self, file_service):
        self.file_service = file_service
    
    def search(self, query):
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