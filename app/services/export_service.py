import io
import csv
from pydub import AudioSegment

class ExportService:
    def __init__(self, file_service):
        self.file_service = file_service

    def export_results_csv(self, results):
        """Export search results to CSV"""
        output = io.StringIO()
        output.write('\ufeff')  # UTF-8 BOM for Excel compatibility
        writer = csv.writer(output, dialect='excel')
        writer.writerow(['Source', 'Text', 'Start Time', 'End Time'])
        
        for result in results:
            text = result['text'].encode('utf-8', errors='replace').decode('utf-8')
            writer.writerow([
                result['source'],
                text,
                result['start'],
                result.get('end', '')
            ])
        
        output.seek(0)
        return output.getvalue()

    def export_audio_segment(self, source, start_time, duration=10):
        """Export a segment of an audio file"""
        available_files = self.file_service.get_available_files()
        if source not in available_files:
            raise ValueError(f"Source not found: {source}")
            
        file_info = available_files[source]
        audio_path = file_info['audio_path']
        audio_format = file_info['audio_format']
        
        # Load the audio file
        audio = AudioSegment.from_file(audio_path, format=audio_format)
        
        # Convert times to milliseconds
        start_ms = int(start_time * 1000)
        duration_ms = int(duration * 1000)
        
        # Validate start time
        if start_ms >= len(audio):
            raise ValueError(f"Start time {start_time}s exceeds audio length {len(audio)/1000}s")
        
        # Adjust duration if needed
        if start_ms + duration_ms > len(audio):
            duration_ms = len(audio) - start_ms
        
        # Extract the segment
        segment = audio[start_ms:start_ms + duration_ms]
        
        # Export to buffer
        buffer = io.BytesIO()
        segment.export(buffer, format=audio_format)
        buffer.seek(0)
        
        return buffer, audio_format 