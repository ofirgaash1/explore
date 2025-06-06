// results.js – lightweight client for Explore search results
// ---------------------------------------------------------------
// Assumptions
//   • Every .result-item carries data attributes:
//       data-source   recording_id (url‑encoded)
//       data-epi      episode_idx (int)
//       data-char     char_offset (int)
//       data-seg      segment_idx (int)  – first segment (already known)
//       data-start    start_sec   (float)
//   • A single audio file per recording lives at /audio/<id>.opus
//   • The server exposes:
//       GET /search/segment?episode_idx&char_offset
//       GET /search/segment/by_idx?episode_idx&seg_idx
// ---------------------------------------------------------------

/* ========================
   1 ‑ Timing instrumentation
   ======================== */
   const timingLogger = {
    timestamps: {},
    requestId: '',

    init(requestId = '') {
        this.requestId = requestId;
    },
    start(ev, data = {}) {
        this.timestamps[ev] = { t0: performance.now(), data };
    },
    end(ev, extra = {}) {
        const rec = this.timestamps[ev];
        if (!rec) return 0;
        const dur = performance.now() - rec.t0;
        delete this.timestamps[ev];
        const payload = { ...rec.data, ...extra, duration_ms: dur, request_id: this.requestId };
        console.log(`[TIMING] ${ev} – ${dur.toFixed(1)} ms`, payload);
        fetch('/api/log-timing', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_type: ev, data: payload }), keepalive: true
        }).catch(() => {});
        return dur;
    },
    log(ev, data = {}) { this.end(ev, data); }
};

/* ========================
   2 ‑ Audio single‑instance manager
   ======================== */
const audioManager = {
    current: null,
    players: new Map(), // Map to store all audio players

    register(audio, id) {
        this.players.set(id, audio);
        audio.addEventListener('play', () => {
            if (this.current && this.current !== audio) this.current.pause();
            this.current = audio;
        });
        audio.addEventListener('ended', () => { if (this.current === audio) this.current = null; });
        audio.addEventListener('pause', () => { if (this.current === audio) this.current = null; });
        return audio;
    },
    stop() { 
        if (this.current) this.current.pause();
        this.current = null;
    },
    getPlayer(id) {
        return this.players.get(id);
    }
};

/* ========================
   3 ‑ Lazy audio loading queue
   ======================== */
const audioQueue = {
    q: [], active: 0, max: 3,
    add(ph) {
        if (!ph || !ph.isConnected) return;
        this.q.push(ph); this.tick();
    },
    tick() {
        if (this.active >= this.max || !this.q.length) return;
        const ph = this.q.shift();
        this.active++;
        const audio = loadAudio(ph);
        audio.addEventListener('loadedmetadata', () => { this.active--; this.tick(); });
        audio.addEventListener('error',           () => { this.active--; this.tick(); });
    }
};

function loadAudio(placeholder) {
    const srcId = placeholder.dataset.source;
    const fmt   = placeholder.dataset.format || 'opus';
    const start = parseFloat(placeholder.dataset.start) || 0;
    const audioUrl = `/audio/${srcId}.${fmt}#t=${start}`;
    const playerId = `audio-${srcId}-${start}`;

    timingLogger.start('audio_loading', { source_id: srcId, start_time: start });

    const cont  = document.createElement('div'); 
    cont.className = 'audio-container';
    cont.dataset.playerId = playerId;
    
    const audio = document.createElement('audio'); 
    audio.controls = true; 
    audio.preload = 'metadata';
    audio.id = playerId;
    
    const src   = document.createElement('source'); 
    src.src = audioUrl;
    src.type = fmt === 'opus' ? 'audio/ogg; codecs=opus' : fmt === 'mp3' ? 'audio/mpeg' : `audio/${fmt}`;
    
    audio.appendChild(src); 
    cont.appendChild(audio); 
    placeholder.replaceWith(cont);

    audio.addEventListener('loadedmetadata', () => timingLogger.end('audio_loading'));
    audioManager.register(audio, playerId);
    return audio;
}

/* ========================
   4 ‑ Segment fetch helpers
   ======================== */
const segmentCache = {};   // key = `${epi}|${idx}`

function fetchSegmentByChar(epi, charOff) {
    return fetch(`/search/segment?episode_idx=${epi}&char_offset=${charOff}`)
            .then(r => r.json());
}

function fetchSegmentByIdx(epi, idx) {
    const k = `${epi}|${idx}`;
    if (segmentCache[k]) return Promise.resolve(segmentCache[k]);
    return fetch(`/search/segment/by_idx?episode_idx=${epi}&seg_idx=${idx}`)
           .then(r => r.json())
           .then(j => (segmentCache[k] = j));
}

// Global batch queue for segment fetches
const segmentBatchQueue = {
    queue: new Map(), // Map<episode_idx, Set<segment_idx>>
    timeout: null,
    
    add(epi, idx) {
        if (!this.queue.has(epi)) {
            this.queue.set(epi, new Set());
        }
        this.queue.get(epi).add(idx);
        
        // Schedule a fetch if not already scheduled
        if (!this.timeout) {
            this.timeout = setTimeout(() => this.flush(), 50); // 50ms debounce
        }
    },
    
    async flush() {
        if (this.queue.size === 0) return;
        
        // Convert queue to lookups array
        const lookups = Array.from(this.queue.entries()).map(([epi, indices]) => ({
            episode_idx: epi,
            seg_indices: Array.from(indices)
        }));
        
        // Clear queue
        this.queue.clear();
        this.timeout = null;
        
        try {
            const response = await fetch('/search/segment/by_idx', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lookups })
            });
            
            const results = await response.json();
            
            // Cache all segments
            results.forEach(result => {
                result.segments.forEach(seg => {
                    segmentCache[`${result.episode_idx}|${seg.segment_index}`] = seg;
                });
            });
            
            // Trigger any pending promises
            this.resolvePendingPromises();
        } catch (error) {
            console.error('Error fetching segments:', error);
            this.rejectPendingPromises(error);
        }
    },
    
    pendingPromises: [],
    
    addPendingPromise(resolve, reject) {
        this.pendingPromises.push({ resolve, reject });
    },
    
    resolvePendingPromises() {
        this.pendingPromises.forEach(({ resolve }) => resolve());
        this.pendingPromises = [];
    },
    
    rejectPendingPromises(error) {
        this.pendingPromises.forEach(({ reject }) => reject(error));
        this.pendingPromises = [];
    }
};

function fetchSegmentsByIdxBatch(epi, indices) {
    // Filter out already cached segments
    const uncachedIndices = indices.filter(idx => !segmentCache[`${epi}|${idx}`]);
    
    if (uncachedIndices.length === 0) {
        // All segments are cached, return them
        return Promise.resolve(indices.map(idx => segmentCache[`${epi}|${idx}`]));
    }
    
    // Add uncached segments to the batch queue
    uncachedIndices.forEach(idx => segmentBatchQueue.add(epi, idx));
    
    // Return a promise that resolves when the batch is processed
    return new Promise((resolve, reject) => {
        segmentBatchQueue.addPendingPromise(resolve, reject);
    }).then(() => indices.map(idx => segmentCache[`${epi}|${idx}`]));
}

/* ========================
   5 ‑ Text highlighting utils
   ======================== */
const queryTerm = new URLSearchParams(window.location.search).get('q') || '';
function highlightQuery(txt, charOffset) {
    if (!queryTerm || charOffset === undefined) return txt;
    const escaped = queryTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'i');
    const match = txt.slice(charOffset).match(regex);
    if (!match) return txt;
    
    const matchLength = match[0].length;
    return txt.slice(0, charOffset) + 
           `<strong>${txt.slice(charOffset, charOffset + matchLength)}</strong>` + 
           txt.slice(charOffset + matchLength);
}

/* ========================
   6 ‑ Build context & navigation
   ======================== */
function buildContext(resultItem, seg) {
    let curIdx = seg.segment_index;
    const epi = resultItem.dataset.epi;
    const charOffset = parseInt(resultItem.dataset.char);

    const ctx = document.createElement('div');
    ctx.className = 'context-container';
    
    // Fetch segments before and after
    const fetchSegments = async () => {
        // Calculate all segment indices we need
        const indices = [];
        for (let i = curIdx - 5; i <= curIdx + 5; i++) {
            if (i >= 0) {
                indices.push(i);
            }
        }
        
        try {
            const segments = await fetchSegmentsByIdxBatch(epi, indices);
            return segments;
        } catch (e) {
            console.error('Error fetching segments:', e);
            return [seg]; // Return at least the current segment on error
        }
    };

    // Render all segments
    const renderSegments = (segments) => {
        return segments.map(s => {
            // Only highlight the exact match in the current segment
            const shouldHighlight = s.segment_index === curIdx;
            const text = shouldHighlight ? highlightQuery(s.text, charOffset) : s.text;
            return `
                <div class="context-segment ${s.segment_index === curIdx ? 'current-segment' : ''}"
                     data-start="${s.start_sec}" 
                     data-seg="${s.segment_index}">
                    ${text}
                </div>
            `;
        }).join('');
    };

    // Initial loading state
    ctx.innerHTML = '<div class="loading">Loading context...</div>';
    
    // Find the result text container and append the context
    const resultTextContainer = resultItem.querySelector('.result-text-container');
    if (resultTextContainer) {
        // Clear any existing content except the audio player
        const audioPlayer = resultTextContainer.querySelector('.audio-container');
        resultTextContainer.innerHTML = '';
        if (audioPlayer) {
            resultTextContainer.appendChild(audioPlayer);
        }
        resultTextContainer.appendChild(ctx);
    }

    // Fetch and render segments
    fetchSegments().then(segments => {
        ctx.innerHTML = renderSegments(segments);
        
        // Add click handlers to all segments
        ctx.querySelectorAll('.context-segment').forEach(segment => {
            segment.addEventListener('click', e => {
                // Pass both the result item's segment index and the clicked segment's start time
                playFromSourceAudio(resultItem.dataset.source, resultItem.dataset.seg, e.target.dataset.start);
            });
        });
    });

    resultItem.dataset.ctxLoaded = '1';
}

/* ========================
   8 ‑ Result‑item click binding
   ======================== */
document.addEventListener('DOMContentLoaded', () => {
    // timing logger init
    const rq = document.querySelector('meta[name="request-id"]');
    if (rq) timingLogger.init(rq.content);

    // Remove any existing source-level audio players
    document.querySelectorAll('.source-header .audio-container').forEach(container => {
        container.remove();
    });

    // Create audio players for all result items
    document.querySelectorAll('.result-item').forEach((item, index) => {
        // Add hit index to the result item
        item.dataset.hitIndex = index;
        
        // Create audio player for this hit
        const srcId = decodeURIComponent(item.dataset.source);
        const start = parseFloat(item.dataset.start) || 0;
        const segIdx = parseInt(item.dataset.segId) || 0;
        const playerId = `audio-hit-${index}`;
        const audioUrl = `/audio/${encodeURIComponent(srcId)}.opus#t=${start}`;

        const audioContainer = document.createElement('div');
        audioContainer.className = 'audio-container';
        audioContainer.dataset.playerId = playerId;
        audioContainer.dataset.source = srcId;
        audioContainer.dataset.segId = segIdx;

        const audio = document.createElement('audio');
        audio.controls = true;
        audio.preload = 'none'; // Don't preload until we set the start time
        audio.id = playerId;
        audio.dataset.source = srcId;
        audio.dataset.segId = segIdx;

        // Set buffer limits
        audio.addEventListener('loadedmetadata', () => {
            // Set buffer size to 10 seconds or 100KB, whichever is smaller
            const bufferSize = Math.min(10, 100 / (audio.duration * 128)); // 128kbps is typical for opus
            audio.buffered.end = bufferSize;
        });

        const src = document.createElement('source');
        src.src = audioUrl;
        src.type = 'audio/ogg; codecs=opus';
        
        audio.appendChild(src);
        audioContainer.appendChild(audio);

        // Insert the audio player at the start of the result item
        const resultTextContainer = item.querySelector('.result-text-container');
        if (resultTextContainer) {
            resultTextContainer.insertBefore(audioContainer, resultTextContainer.firstChild);
        }

        // Register the audio player
        audioManager.register(audio, playerId);

        // Load segment data
        const epi = item.dataset.epi;
        const char = item.dataset.char;
        fetchSegmentByChar(epi, char).then(seg => {
            buildContext(item, seg);
            item.dataset.ctxLoaded = '1';
        });
    });
});

/* ========================
   7 ‑ Audio helper to seek header player
   ======================== */
function playFromSourceAudio(sourceId, segIdx, startTime) {
    // Find the result item that matches this source and segment
    const resultItem = document.querySelector(`.result-item[data-source="${sourceId}"][data-seg="${segIdx}"]`);
    if (!resultItem) {
        console.warn(`Could not find result item for source: ${sourceId} and segment: ${segIdx}`);
        return;
    }

    // Get the audio player directly from the result item
    const audio = resultItem.querySelector('audio');
    if (!audio) {
        console.warn(`Could not find audio element in result item`);
        return;
    }

    // Stop all other players
    audioManager.stop();
    
    // Set the start time and load the audio
    audio.currentTime = parseFloat(startTime);
    audio.preload = 'metadata'; // Start loading after setting the time
    
    // Play the audio
    audio.play().catch(err => {
        console.error('Error playing audio:', err);
    });
}

/* ========================
   9 ‑ Lazy audio via IntersectionObserver
   ======================== */
function setupLazyLoading() {
    if (!('IntersectionObserver' in window)) {
        document.querySelectorAll('.audio-placeholder').forEach(p => audioQueue.add(p));
        return;
    }
    const io = new IntersectionObserver(entries => {
        entries.forEach(e => { if (e.isIntersecting) audioQueue.add(e.target); });
    }, { rootMargin: '50px' });
    document.querySelectorAll('.audio-placeholder').forEach(p => io.observe(p));
}
