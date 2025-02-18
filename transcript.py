import faster_whisper
import stable_whisper

model = faster_whisper.WhisperModel('ivrit-ai/whisper-large-v3-turbo-ct2')
stable_model = stable_whisper.load_model('ivrit-ai/whisper-large-v3-turbo-ct2')

# Get basic transcription from faster-whisper
segs, _ = model.transcribe('media-file', language='he')
texts = [s.text for s in segs]
transcribed_text = ' '.join(texts)
print(f'Transcribed text: {transcribed_text}')

# Get timed transcription using stable-ts
result = stable_model.transcribe('media-file', language='he')
word_timestamps = result.word_timestamps

# Print words with their timestamps
for word_info in word_timestamps:
    word = word_info.word
    start = word_info.start
    end = word_info.end
    print(f'Word: {word}, Start: {start:.2f}s, End: {end:.2f}s')