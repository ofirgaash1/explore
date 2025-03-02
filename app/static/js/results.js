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
    
    const audioContainer = document.createElement('div');
    audioContainer.className = 'audio-container';
    
    // Create audio element
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.preload = "metadata";
    audio.dataset.currentTime = start;
    
    const sourceElement = document.createElement('source');
    sourceElement.src = `${audioUrl}#t=${start}`;
    sourceElement.type = `audio/${format}`;
    
    audio.appendChild(sourceElement);
    audioContainer.appendChild(audio);
    
    // Add audio navigation buttons
    const audioControls = document.createElement('div');
    audioControls.className = 'audio-controls';
    
    // Add 15-second back button
    const back15Btn = document.createElement('button');
    back15Btn.className = 'audio-btn';
    back15Btn.textContent = '⏪ -15s';
    back15Btn.onclick = function() { skipAudio(audio, -15); };
    
    // Add 5-second back button
    const back5Btn = document.createElement('button');
    back5Btn.className = 'audio-btn';
    back5Btn.textContent = '◀ -5s';
    back5Btn.onclick = function() { skipAudio(audio, -5); };
    
    // Add 5-second forward button
    const forward5Btn = document.createElement('button');
    forward5Btn.className = 'audio-btn';
    forward5Btn.textContent = '+5s ▶';
    forward5Btn.onclick = function() { skipAudio(audio, 5); };
    
    // Add 15-second forward button
    const forward15Btn = document.createElement('button');
    forward15Btn.className = 'audio-btn';
    forward15Btn.textContent = '+15s ⏩';
    forward15Btn.onclick = function() { skipAudio(audio, 15); };
    
    // Add buttons to controls in order
    audioControls.appendChild(back15Btn);
    audioControls.appendChild(back5Btn);
    audioControls.appendChild(forward5Btn);
    audioControls.appendChild(forward15Btn);
    
    audioContainer.appendChild(audioControls);
    
    placeholder.replaceWith(audioContainer);
    return audio;
}

function skipAudio(audio, seconds) {
    const newTime = Math.max(0, audio.currentTime + seconds);
    audio.currentTime = newTime;
    audio.dataset.currentTime = newTime;
}

function formatTime(seconds) {
    // Handle hours if needed
    if (seconds >= 3600) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    } else {
        // Original minutes:seconds format
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
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
    const prevSegments = [];
    for (let i = Math.max(0, currentIndex - 2); i < currentIndex; i++) {
        prevSegments.push(segments[i]);
    }
    
    const currentSegment = segments[currentIndex];
    
    const nextSegments = [];
    for (let i = currentIndex + 1; i <= Math.min(segments.length - 1, currentIndex + 2); i++) {
        nextSegments.push(segments[i]);
    }
    
    // Create context HTML
    let contextHtml = '';
    
    // Add previous segments if available
    prevSegments.forEach((segment, idx) => {
        contextHtml += `<div class="context-segment prev-segment" data-start="${segment.start}" data-index="${currentIndex - (prevSegments.length - idx)}">
            <span class="segment-time">${formatTime(segment.start)}</span>
            ${segment.text}
        </div>`;
    });
    
    // Add current segment with highlighted query
    let currentText = currentSegment.text;
    if (query) {
        // Escape special regex characters in the query
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Create a regex that matches the query with word boundaries (if possible)
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        currentText = currentText.replace(regex, '<strong>$1</strong>');
    }
    
    contextHtml += `<div class="context-segment current-segment" data-start="${currentSegment.start}" data-index="${currentIndex}">
        <span class="segment-time">${formatTime(currentSegment.start)}</span>
        ${currentText}
    </div>`;
    
    // Add next segments if available
    nextSegments.forEach((segment, idx) => {
        contextHtml += `<div class="context-segment next-segment" data-start="${segment.start}" data-index="${currentIndex + idx + 1}">
            <span class="segment-time">${formatTime(segment.start)}</span>
            ${segment.text}
        </div>`;
    });
    
    // Update the result text
    const textContainer = resultItem.querySelector('.result-text-container');
    const resultText = resultItem.querySelector('.result-text');
    
    // Replace the single result text with the context container
    const contextContainer = document.createElement('div');
    contextContainer.className = 'context-container';
    contextContainer.innerHTML = contextHtml;
    
    // Add click event listeners to segments for audio playback
    contextContainer.querySelectorAll('.context-segment').forEach(segment => {
        segment.addEventListener('click', function() {
            playSegmentAudio(resultItem, this.dataset.start, source);
        });
    });
    
    // Add context scroller controls
    const scrollerControls = document.createElement('div');
    scrollerControls.className = 'context-scroller';
    scrollerControls.innerHTML = `
        <button class="scroller-btn" data-direction="up" title="Scroll up to earlier segments">▲ Earlier</button>
        <span class="scroller-position">Segment ${currentIndex + 1} of ${segments.length}</span>
        <button class="scroller-btn" data-direction="down" title="Scroll down to later segments">Later ▼</button>
    `;
    
    // Add event listeners to scroller buttons
    scrollerControls.querySelectorAll('.scroller-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            scrollContext(resultItem, this.dataset.direction);
        });
    });
    
    // Store the current index in the result item for reference
    resultItem.dataset.currentIndex = currentIndex;
    
    // Replace the text with the context container and scroller
    if (resultText) {
        resultText.replaceWith(contextContainer);
        textContainer.insertBefore(scrollerControls, textContainer.firstChild);
    } else {
        // If we're updating an existing context view
        const existingContext = textContainer.querySelector('.context-container');
        const existingScroller = textContainer.querySelector('.context-scroller');
        
        if (existingContext) {
            existingContext.innerHTML = contextHtml;
            
            // Re-add click event listeners to segments
            existingContext.querySelectorAll('.context-segment').forEach(segment => {
                segment.addEventListener('click', function() {
                    playSegmentAudio(resultItem, this.dataset.start, source);
                });
            });
        } else {
            textContainer.appendChild(contextContainer);
        }
        
        if (existingScroller) {
            existingScroller.querySelector('.scroller-position').textContent = 
                `Segment ${currentIndex + 1} of ${segments.length}`;
        } else {
            textContainer.insertBefore(scrollerControls, textContainer.firstChild);
        }
    }
}

function playSegmentAudio(resultItem, startTime, source) {
    // Update the export segment link
    const exportLink = resultItem.querySelector('.btn-export[href*="export/segment"]');
    if (exportLink) {
        exportLink.href = `/export/segment/${encodeURIComponent(source)}?start=${startTime}&duration=10`;
    }
    
    // Update the audio element or placeholder
    const audioPlaceholder = resultItem.querySelector('.audio-placeholder');
    if (audioPlaceholder) {
        // If we still have a placeholder, update its data and load the audio
        audioPlaceholder.dataset.start = startTime;
        const audio = loadAudio(audioPlaceholder);
        audio.currentTime = startTime;
        audio.play();
    } else {
        // If we already have an audio element, update its source
        const audio = resultItem.querySelector('audio');
        const sourceElement = audio.querySelector('source');
        const format = sourceElement.type.split('/')[1];
        
        // Update the source URL with the new start time
        sourceElement.src = `/audio/${encodeURIComponent(source)}.${format}#t=${startTime}`;
        
        // Update the data attribute for future reference
        audio.dataset.currentTime = startTime;
        
        // Reload and play the audio
        audio.load();
        audio.currentTime = startTime;
        audio.play();
    }
}

function scrollContext(resultItem, direction) {
    const source = decodeURIComponent(resultItem.dataset.source);
    const currentIndex = parseInt(resultItem.dataset.currentIndex);
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) return;
    
    let newIndex;
    
    if (direction === 'up') {
        // Move up 3 segments if possible, or to the beginning
        newIndex = Math.max(0, currentIndex - 3);
    } else {
        // Move down 3 segments if possible, or to the end
        newIndex = Math.min(segments.length - 1, currentIndex + 3);
    }
    
    // If we're already at the limit, don't do anything
    if (newIndex === currentIndex) return;
    
    // Update to the new segment without changing audio
    updateSegmentContext(resultItem, segments[newIndex], source);
}

function prevSegment(button) {
    // Navigate up to the result-item from the button
    const resultItem = button.closest('.result-item');
    
    // Get source and current index
    const source = decodeURIComponent(resultItem.dataset.source);
    const currentIndex = parseInt(resultItem.dataset.currentIndex);
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) {
        // If segments aren't loaded yet, try to load them from the server
        const jsonPath = `/export/source/${encodeURIComponent(source)}?type=json`;
        initializeSourceSegments(source, jsonPath);
        return;
    }
    
    // If we found the current segment and it's not the first one
    if (currentIndex > 0) {
        const prevSegment = segments[currentIndex - 1];
        updateSegmentContext(resultItem, prevSegment, source);
    }
}

function nextSegment(button) {
    // Navigate up to the result-item from the button
    const resultItem = button.closest('.result-item');
    
    // Get source and current index
    const source = decodeURIComponent(resultItem.dataset.source);
    const currentIndex = parseInt(resultItem.dataset.currentIndex);
    
    // Get segments for this source
    const segments = sourceSegments[source];
    if (!segments) {
        // If segments aren't loaded yet, try to load them from the server
        const jsonPath = `/export/source/${encodeURIComponent(source)}?type=json`;
        initializeSourceSegments(source, jsonPath);
        return;
    }
    
    // If we found the current segment and it's not the last one
    if (currentIndex < segments.length - 1) {
        const nextSegment = segments[currentIndex + 1];
        updateSegmentContext(resultItem, nextSegment, source);
    }
}

function updateSegmentContext(resultItem, segment, source) {
    // Update the data attribute for the result item
    resultItem.dataset.start = segment.start;
    
    // Update the context display only
    addContextToResult(resultItem);
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