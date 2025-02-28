// Store all segments data for each source
const sourceSegments = {};

// Initialize segments data from server
function initializeSourceSegments(source, jsonPath) {
    fetch(jsonPath)
        .then(response => response.json())
        .then(data => {
            if (data && data.segments) {
                sourceSegments[source] = data.segments;
                
                // After loading segments, update all result items for this source to show context
                document.querySelectorAll(`.result-item[data-source="${source}"]`).forEach(item => {
                    addContextToResult(item);
                });
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

function addContextToResult(resultItem) {
    const source = decodeURIComponent(resultItem.dataset.source);
    const start = parseFloat(resultItem.dataset.start);
    const query = document.querySelector('input[name="q"]').value.toLowerCase();
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) {
        return; // Segments not loaded yet
    }
    
    // Find current segment index
    const currentIndex = findSegmentIndex(start, segments);
    if (currentIndex === -1) return;
    
    // Get previous, current, and next segments
    const prevSegment = currentIndex > 0 ? segments[currentIndex - 1] : null;
    const currentSegment = segments[currentIndex];
    const nextSegment = currentIndex < segments.length - 1 ? segments[currentIndex + 1] : null;
    
    // Create context HTML
    let contextHtml = '';
    
    // Add previous segment if available
    if (prevSegment) {
        contextHtml += `<div class="context-segment prev-segment">${prevSegment.text}</div>`;
    }
    
    // Add current segment with highlighted query
    let currentText = currentSegment.text;
    if (query) {
        // Escape special regex characters in the query
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Create a regex that matches the query with word boundaries (if possible)
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        currentText = currentText.replace(regex, '<strong>$1</strong>');
    }
    
    contextHtml += `<div class="context-segment current-segment">${currentText}</div>`;
    
    // Add next segment if available
    if (nextSegment) {
        contextHtml += `<div class="context-segment next-segment">${nextSegment.text}</div>`;
    }
    
    // Update the result text
    const textContainer = resultItem.querySelector('.result-text-container');
    const resultText = resultItem.querySelector('.result-text');
    
    // Replace the single result text with the context container
    const contextContainer = document.createElement('div');
    contextContainer.className = 'context-container';
    contextContainer.innerHTML = contextHtml;
    
    resultText.replaceWith(contextContainer);
}

function prevSegment(button) {
    // Navigate up to the result-item from the button
    const resultItem = button.closest('.result-item');
    
    // Get source and current time
    const source = decodeURIComponent(resultItem.dataset.source);
    
    // Find either the audio-placeholder or the audio element
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    const audio = resultItem.querySelector('audio');
    
    // Get the current time from either the placeholder or the audio element
    const currentTime = parseFloat(audioPlaceholder ? 
                                  audioPlaceholder.dataset.start : 
                                  audio.dataset.currentTime);
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) {
        // If segments aren't loaded yet, try to load them from the server
        const jsonPath = `/export/source/${encodeURIComponent(source)}?type=json`;
        initializeSourceSegments(source, jsonPath);
        return;
    }
    
    // Find current segment index
    const currentIndex = findSegmentIndex(currentTime, segments);
    
    // If we found the current segment and it's not the first one
    if (currentIndex > 0) {
        const prevSegment = segments[currentIndex - 1];
        updateSegment(resultItem, prevSegment, source);
    }
}

function nextSegment(button) {
    // Navigate up to the result-item from the button
    const resultItem = button.closest('.result-item');
    
    // Get source and current time
    const source = decodeURIComponent(resultItem.dataset.source);
    
    // Find either the audio-placeholder or the audio element
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    const audio = resultItem.querySelector('audio');
    
    // Get the current time from either the placeholder or the audio element
    const currentTime = parseFloat(audioPlaceholder ? 
                                  audioPlaceholder.dataset.start : 
                                  audio.dataset.currentTime);
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) {
        // If segments aren't loaded yet, try to load them from the server
        const jsonPath = `/export/source/${encodeURIComponent(source)}?type=json`;
        initializeSourceSegments(source, jsonPath);
        return;
    }
    
    // Find current segment index
    const currentIndex = findSegmentIndex(currentTime, segments);
    
    // If we found the current segment and it's not the last one
    if (currentIndex < segments.length - 1) {
        const nextSegment = segments[currentIndex + 1];
        updateSegment(resultItem, nextSegment, source);
    }
}

function updateSegment(resultItem, segment, source) {
    // Update the data attribute for the result item
    resultItem.dataset.start = segment.start;
    
    // Update the context display
    addContextToResult(resultItem);
    
    // Update the audio element or placeholder
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    if (audioPlaceholder) {
        // If we still have a placeholder, update its data and load the audio
        audioPlaceholder.dataset.start = segment.start;
        const audio = loadAudio(audioPlaceholder);
        audio.currentTime = segment.start;
        audio.play();
    } else {
        // If we already have an audio element, update its source
        const audio = resultItem.querySelector('audio');
        const sourceElement = audio.querySelector('source');
        const format = sourceElement.type.split('/')[1];
        
        // Update the source URL with the new start time
        sourceElement.src = `/audio/${encodeURIComponent(source)}.${format}#t=${segment.start}`;
        
        // Update the data attribute for future reference
        audio.dataset.currentTime = segment.start;
        
        // Reload and play the audio
        audio.load();
        audio.currentTime = segment.start;
        audio.play();
    }
    
    // Update the export segment link
    const exportLink = resultItem.querySelector('.btn-export[href*="export/segment"]');
    if (exportLink) {
        exportLink.href = `/export/segment/${encodeURIComponent(source)}?start=${segment.start}&duration=10`;
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
        
        // Load segments data for navigation if not already loaded
        if (!sourceSegments[sourceId]) {
            const jsonPath = `/export/source/${encodeURIComponent(sourceId)}?type=json`;
            initializeSourceSegments(sourceId, jsonPath);
        }
    } else {
        resultsDiv.style.display = 'none';
        icon.textContent = '▶';
    }
}

// Initialize segments data when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // For each source group, preload its segments data
    document.querySelectorAll('.source-group').forEach(group => {
        const sourceId = group.querySelector('.source-header').getAttribute('onclick').match(/'([^']+)'/)[1];
        const jsonPath = `/export/source/${encodeURIComponent(sourceId)}?type=json`;
        initializeSourceSegments(sourceId, jsonPath);
    });
}); 