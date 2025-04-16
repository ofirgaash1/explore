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
    
    // Set the correct MIME type based on format
    if (format === 'opus') {
        sourceElement.type = 'audio/ogg; codecs=opus';  // Correct MIME type for Opus
    } else if (format === 'ogg') {
        sourceElement.type = 'audio/ogg';
    } else if (format === 'mp3') {
        sourceElement.type = 'audio/mpeg';
    } else {
        sourceElement.type = `audio/${format}`;
    }
    
    audio.appendChild(sourceElement);
    audioContainer.appendChild(audio);
    
    // Add audio navigation buttons
    const audioControls = document.createElement('div');
    audioControls.className = 'audio-controls';
    
    // Add 15-second back button
    const back15Btn = document.createElement('button');
    back15Btn.className = 'audio-btn';
    back15Btn.textContent = '⏪ -15ש';
    back15Btn.onclick = function() { skipAudio(audio, -15); };
    
    // Add 5-second back button
    const back5Btn = document.createElement('button');
    back5Btn.className = 'audio-btn';
    back5Btn.textContent = '◀ -5ש';
    back5Btn.onclick = function() { skipAudio(audio, -5); };
    
    // Add 5-second forward button
    const forward5Btn = document.createElement('button');
    forward5Btn.className = 'audio-btn';
    forward5Btn.textContent = '+5ש ▶';
    forward5Btn.onclick = function() { skipAudio(audio, 5); };
    
    // Add 15-second forward button
    const forward15Btn = document.createElement('button');
    forward15Btn.className = 'audio-btn';
    forward15Btn.textContent = '+15ש ⏩';
    forward15Btn.onclick = function() { skipAudio(audio, 15); };
    
    // Add buttons to controls in order
    audioControls.appendChild(forward15Btn);
    audioControls.appendChild(forward5Btn);
    audioControls.appendChild(back5Btn);
    audioControls.appendChild(back15Btn);

    
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
       <button class="scroller-btn" data-direction="up" title="לקטעים מוקדמים יותר">▲ הקודם</button>
        <span class="scroller-position">קטע ${currentIndex + 1} מתוך ${segments.length}</span>
       <button class="scroller-btn" data-direction="down" title="לקטעים בהמשך">הבא ▼</button>
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
                `קטע ${currentIndex + 1} מתוך ${segments.length}`;
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
        audio.play();
    } else {
        // If we already have an audio element, update its source
        const audio = resultItem.querySelector('audio');
        const sourceElement = audio.querySelector('source');
        const format = sourceElement.type.split('/')[1];
        const newSrc = `/audio/${encodeURIComponent(source)}.${format}#t=${startTime}`;

        if (audio.src !== newSrc) {
            audio.src = newSrc;
            audio.load();
        }
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

// Function to update pagination UI
function updatePagination(pagination) {
    console.log("Updating pagination:", pagination);
    
    // Only create/update the bottom pagination
    ensureBottomPaginationContainer();
    
    const paginationElement = document.querySelector('.bottom-pagination');
    if (!paginationElement) {
        console.warn("No pagination element found");
        return;
    }
    
    // Get current search parameters
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('q');
    const regex = searchParams.has('regex');
    const substring = searchParams.has('substring');
    const maxResults = parseInt(searchParams.get('max_results') || '100');
    
    // Create pagination info div
    const paginationInfo = document.createElement('div');
    paginationInfo.className = 'pagination-info';
    paginationInfo.textContent = `עמוד ${pagination.page} מתוך ${pagination.total_pages}`;
    
    // Create pagination controls div
    const paginationControls = document.createElement('div');
    paginationControls.className = 'pagination-controls';
    
    // Add previous button if needed
    if (pagination.has_prev) {
        const prevButton = document.createElement('a');
        prevButton.href = `/search?q=${encodeURIComponent(query)}&page=${pagination.page - 1}` +
                         `&max_results=${maxResults}` +
                         (regex ? '&regex=true' : '') +
                         (substring ? '&substring=true' : '');
        prevButton.className = 'pagination-btn';
        prevButton.textContent = '← הקודם';
        paginationControls.appendChild(prevButton);
    } else {
        const prevButton = document.createElement('span');
        prevButton.className = 'pagination-btn disabled';
        prevButton.textContent = '← הקודם';
        paginationControls.appendChild(prevButton);
    }
    
    // Add page numbers
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.total_pages, startPage + 4);
    
    if (startPage > 1) {
        const firstPageLink = document.createElement('a');
        firstPageLink.href = `/search?q=${encodeURIComponent(query)}&page=1` +
                           `&max_results=${maxResults}` +
                           (regex ? '&regex=true' : '') +
                           (substring ? '&substring=true' : '');
        firstPageLink.className = 'pagination-btn';
        firstPageLink.textContent = '1';
        paginationControls.appendChild(firstPageLink);
        
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'pagination-ellipsis';
            ellipsis.textContent = '...';
            paginationControls.appendChild(ellipsis);
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        if (i === pagination.page) {
            const activePageBtn = document.createElement('span');
            activePageBtn.className = 'pagination-btn active';
            activePageBtn.textContent = i.toString();
            paginationControls.appendChild(activePageBtn);
        } else {
            const pageLink = document.createElement('a');
            pageLink.href = `/search?q=${encodeURIComponent(query)}&page=${i}` +
                           `&max_results=${maxResults}` +
                           (regex ? '&regex=true' : '') +
                           (substring ? '&substring=true' : '');
            pageLink.className = 'pagination-btn';
            pageLink.textContent = i.toString();
            paginationControls.appendChild(pageLink);
        }
    }
    
    if (endPage < pagination.total_pages) {
        if (endPage < pagination.total_pages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.className = 'pagination-ellipsis';
            ellipsis.textContent = '...';
            paginationControls.appendChild(ellipsis);
        }
        
        const lastPageLink = document.createElement('a');
        lastPageLink.href = `/search?q=${encodeURIComponent(query)}&page=${pagination.total_pages}` +
                          `&max_results=${maxResults}` +
                          (regex ? '&regex=true' : '') +
                          (substring ? '&substring=true' : '');
        lastPageLink.className = 'pagination-btn';
        lastPageLink.textContent = pagination.total_pages.toString();
        paginationControls.appendChild(lastPageLink);
    }
    
    // Add next button if needed
    if (pagination.has_next) {
        const nextButton = document.createElement('a');
        nextButton.href = `/search?q=${encodeURIComponent(query)}&page=${pagination.page + 1}` +
                         `&max_results=${maxResults}` +
                         (regex ? '&regex=true' : '') +
                         (substring ? '&substring=true' : '');
        nextButton.className = 'pagination-btn';
        nextButton.textContent = 'הבא →';
        paginationControls.appendChild(nextButton);
    } else {
        const nextButton = document.createElement('span');
        nextButton.className = 'pagination-btn disabled';
        nextButton.textContent = 'הבא →';
        paginationControls.appendChild(nextButton);
    }
    
    // Clear and update the pagination element
    paginationElement.innerHTML = '';
    paginationElement.appendChild(paginationInfo);
    paginationElement.appendChild(paginationControls);
    
    // Also update the results count in the stats section
    updateResultsCount(pagination);
}

// Function to ensure only bottom pagination container exists
function ensureBottomPaginationContainer() {
    const resultsContainer = document.querySelector('.results');
    if (!resultsContainer) return;
    
    // Remove any top pagination if it exists
    const topPagination = document.querySelector('.pagination:not(.bottom-pagination)');
    if (topPagination) {
        topPagination.remove();
    }
    
    // Check if bottom pagination exists
    let bottomPagination = document.querySelector('.bottom-pagination');
    if (!bottomPagination) {
        console.log("Creating bottom pagination container");
        bottomPagination = document.createElement('div');
        bottomPagination.className = 'pagination bottom-pagination';
        
        // Insert after results or before search-stats
        const searchStats = document.querySelector('.search-stats');
        if (searchStats) {
            resultsContainer.parentNode.insertBefore(bottomPagination, searchStats);
        } else {
            resultsContainer.parentNode.appendChild(bottomPagination);
        }
    }
}

// Function to update the results count in the stats section
function updateResultsCount(pagination) {
    // Update the stats section at the top
    const statsElement = document.querySelector('.stats');
    if (statsElement) {
        let statsText = '';
        if (pagination.total_results > 0) {
            const start = (pagination.page - 1) * pagination.per_page + 1;
            const end = Math.min(pagination.page * pagination.per_page, pagination.total_results);
            
            if (pagination.still_searching) {
                statsText = `מציג ${start} עד ${end} מתוך ${pagination.total_results} תוצאות שנמצאו עד כה (עדיין מחפש...)`;
                
                // Always remove duration span if still searching
                const durationSpan = statsElement.querySelector('.duration');
                if (durationSpan) {
                    durationSpan.remove();
                }
            } else {
                statsText = `מציג ${start} עד ${end} מתוך ${pagination.total_results} תוצאות`;
            }
        } else {
            statsText = 'לא נמצאו תוצאות';
        }
        
        // Update the stats text without the duration span
        statsElement.innerHTML = statsText;
        
        // We'll only add the duration span when the search is fully complete
        // in the checkForMoreResults function
    }
    
    // Remove the redundant results-count element at the bottom if it exists
    const resultsCountElement = document.getElementById('results-count');
    if (resultsCountElement && resultsCountElement.parentNode) {
        resultsCountElement.parentNode.remove();
    }
}

// Function to check for more results if progressive search is active
function checkForMoreResults() {
    // Store the start time of the progressive search if not already set
    if (!window.searchStartTime) {
        window.searchStartTime = Date.now();
    }
    
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('q');
    const page = parseInt(searchParams.get('page') || '1');
    const regex = searchParams.has('regex');
    const substring = searchParams.has('substring');
    const maxResults = parseInt(searchParams.get('max_results') || '100');
    
    // Build API URL
    const apiUrl = `/search?q=${encodeURIComponent(query)}&page=${page}` + 
                  `&max_results=${maxResults}` +
                  (regex ? '&regex=true' : '') +
                  (substring ? '&substring=true' : '');
    
    // Make AJAX request to check for updated results
    fetch(apiUrl, {
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log("Progressive search update:", data);
        
        // Check if search is still in progress
        if (data.stats.still_searching) {
            // Update pagination if needed
            if (data.pagination.total_pages > 0) {
                updatePagination(data.pagination);
            }
            
            // Check again in 1 second
            setTimeout(checkForMoreResults, 1000);
        } else {
            // Search is complete, update the UI
            updatePagination(data.pagination);
            
            // Calculate total search duration from our stored start time
            const totalDuration = Date.now() - window.searchStartTime;
            
            // Update the search duration now that we have the final time
            const statsElement = document.querySelector('.stats');
            if (statsElement) {
                // Only add the duration span now that the search is complete
                // First ensure any existing one is removed
                const existingDurationSpan = statsElement.querySelector('.duration');
                if (existingDurationSpan) {
                    existingDurationSpan.remove();
                }
                
                // Create a new duration span with the final time
                let durationSpan = document.createElement('span');
                durationSpan.className = 'duration';
                durationSpan.textContent = ` (החיפוש ארך ${totalDuration.toFixed(2)} מילישניות)`;
                statsElement.appendChild(durationSpan);
            }
            
            // Reset the search start time
            window.searchStartTime = null;
            
            // If we have no results on the current page but there are results available,
            // redirect to the first page
            if (data.results.length === 0 && data.stats.total_count > 0 && page > 1) {
                window.location.href = `/search?q=${encodeURIComponent(query)}&page=1` +
                                      `&max_results=${maxResults}` +
                                      (regex ? '&regex=true' : '') +
                                      (substring ? '&substring=true' : '');
            }
        }
    })
    .catch(error => {
        console.error('Error checking for more results:', error);
    });
}

// Initialize progressive loading if needed
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a search results page
    const searchParams = new URLSearchParams(window.location.search);
    const query = searchParams.get('q');
    
    if (query) {
        // Remove any top pagination and ensure only bottom pagination exists
        ensureBottomPaginationContainer();
        
        // Remove the redundant results-count element at the bottom if it exists
        const resultsCountElement = document.getElementById('results-count');
        if (resultsCountElement && resultsCountElement.parentNode) {
            resultsCountElement.parentNode.remove();
        }
        
        // Remove any existing duration span to start fresh
        const statsElement = document.querySelector('.stats');
        if (statsElement) {
            const durationSpan = statsElement.querySelector('.duration');
            if (durationSpan) {
                durationSpan.remove();
            }
        }
        
        // Check if progressive loading is enabled
        const progressive = searchParams.has('progressive');
        if (progressive) {
            console.log("Starting progressive search checks");
            // Start checking for more results
            checkForMoreResults();
        }
    }
    
    // Add progressive parameter to search form
    const searchForm = document.querySelector('.search-form');
    if (searchForm && !searchForm.querySelector('input[name="progressive"]')) {
        console.log("Adding progressive parameter to search form");
        const progressiveInput = document.createElement('input');
        progressiveInput.type = 'hidden';
        progressiveInput.name = 'progressive';
        progressiveInput.value = 'true';
        searchForm.appendChild(progressiveInput);
    }
}); 