// Store all segments data for each source
const sourceSegments = {};

// Initialize segments data from server
function initializeSourceSegments(source, jsonPath) {
    fetch(jsonPath)
        .then(response => response.json())
        .then(data => {
            if (data && data.segments) {
                sourceSegments[source] = data.segments;
            }
        })
        .catch(error => console.error('Error loading segments:', error));
}

function loadAudio(placeholder) {
    const source = placeholder.dataset.source;
    const format = placeholder.dataset.format;
    const start = placeholder.dataset.start;
    const audioUrl = `/audio/${source}.${format}`;
    
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.preload = "metadata";
    audio.dataset.currentTime = start;
    
    const sourceElement = document.createElement('source');
    sourceElement.src = `${audioUrl}#t=${start}`;
    sourceElement.type = `audio/${format}`;
    
    audio.appendChild(sourceElement);
    placeholder.replaceWith(audio);
    return audio;
}

function findSegmentIndex(time, segments) {
    return segments.findIndex(seg => Math.abs(seg.start - parseFloat(time)) < 0.1);
}

function prevSegment(button) {
    const resultItem = button.closest('.result-item');
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    const audio = resultItem.querySelector('audio');
    const source = decodeURIComponent(audioPlaceholder ? audioPlaceholder.dataset.source : resultItem.dataset.source);
    const currentTime = parseFloat(audioPlaceholder ? audioPlaceholder.dataset.start : audio.dataset.currentTime);
    
    const segments = sourceSegments[source];
    if (!segments) return;
    
    const currentIndex = findSegmentIndex(currentTime, segments);
    
    if (currentIndex > 0) {
        const prevSegment = segments[currentIndex - 1];
        updateSegment(resultItem, prevSegment, source);
    }
}

function nextSegment(button) {
    const resultItem = button.closest('.result-item');
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    const audio = resultItem.querySelector('audio');
    const source = decodeURIComponent(audioPlaceholder ? audioPlaceholder.dataset.source : resultItem.dataset.source);
    const currentTime = parseFloat(audioPlaceholder ? audioPlaceholder.dataset.start : audio.dataset.currentTime);
    
    const segments = sourceSegments[source];
    if (!segments) return;
    
    const currentIndex = findSegmentIndex(currentTime, segments);
    
    if (currentIndex < segments.length - 1) {
        const nextSegment = segments[currentIndex + 1];
        updateSegment(resultItem, nextSegment, source);
    }
}

function updateSegment(resultItem, segment, source) {
    const text = resultItem.querySelector('.result-text');
    text.textContent = segment.text;
    
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    if (audioPlaceholder) {
        audioPlaceholder.dataset.start = segment.start;
        const audio = loadAudio(audioPlaceholder);
        audio.currentTime = segment.start;
        audio.play();
    } else {
        const audio = resultItem.querySelector('audio');
        const sourceElement = audio.querySelector('source');
        const format = sourceElement.type.split('/')[1];
        sourceElement.src = `/audio/${encodeURIComponent(source)}.${format}#t=${segment.start}`;
        audio.load();
        audio.currentTime = segment.start;
        audio.play();
    }
}

function toggleSource(sourceId) {
    const resultsDiv = document.getElementById(sourceId + '-results');
    const icon = document.getElementById('icon-' + sourceId);
    
    if (resultsDiv.style.display === 'none') {
        resultsDiv.style.display = 'block';
        icon.textContent = '▼';
        
        // Load audio players when section is expanded
        resultsDiv.querySelectorAll('.audio-placeholder').forEach(placeholder => {
            loadAudio(placeholder);
        });
    } else {
        resultsDiv.style.display = 'none';
        icon.textContent = '▶';
    }
} 