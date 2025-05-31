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
        console.log(`[TIMING] ${ev} – ${dur.toFixed(1)} ms`, payload);
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
    register(audio) {
        audio.addEventListener('play', () => {
            if (this.current && this.current !== audio) this.current.pause();
            this.current = audio;
        });
        audio.addEventListener('ended', () => { if (this.current === audio) this.current = null; });
        audio.addEventListener('pause', () => { if (this.current === audio) this.current = null; });
        return audio;
    },
    stop() { if (this.current) this.current.pause(); }
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

    timingLogger.start('audio_loading', { source_id: srcId, start_time: start });

    const cont  = document.createElement('div'); cont.className = 'audio-container';
    const audio = document.createElement('audio'); audio.controls = true; audio.preload = 'metadata';
    const src   = document.createElement('source'); src.src = audioUrl;
    src.type = fmt === 'opus' ? 'audio/ogg; codecs=opus' : fmt === 'mp3' ? 'audio/mpeg' : `audio/${fmt}`;
    audio.appendChild(src); cont.appendChild(audio); placeholder.replaceWith(cont);

    audio.addEventListener('loadedmetadata', () => timingLogger.end('audio_loading'));
    audioManager.register(audio);
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

function fetchSegmentsByIdxBatch(epi, indices) {
    // Filter out already cached segments
    const uncachedIndices = indices.filter(idx => !segmentCache[`${epi}|${idx}`]);
    
    if (uncachedIndices.length === 0) {
        // All segments are cached, return them
        return Promise.resolve(indices.map(idx => segmentCache[`${epi}|${idx}`]));
    }

    return fetch('/search/segment/by_idx', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            episode_idx: epi,
            seg_indices: uncachedIndices
        })
    })
    .then(r => r.json())
    .then(segments => {
        // Cache the new segments
        segments.forEach(seg => {
            segmentCache[`${epi}|${seg.segment_index}`] = seg;
        });
        
        // Return all requested segments in order
        return indices.map(idx => segmentCache[`${epi}|${idx}`]);
    });
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
            return `
                <div class="context-segment ${s.segment_index === curIdx ? 'current-segment' : ''}"
                     data-start="${s.start_sec}" 
                     data-seg="${s.segment_index}">
                    ${shouldHighlight ? highlightQuery(s.text, charOffset) : s.text}
                </div>
            `;
        }).join('');
    };

    // Initial loading state
    ctx.innerHTML = '<div class="loading">Loading context...</div>';
    resultItem.querySelector('.result-text-container').replaceChildren(ctx);

    // Fetch and render segments
    fetchSegments().then(segments => {
        ctx.innerHTML = renderSegments(segments);
        
        // Add click handlers to all segments
        ctx.querySelectorAll('.context-segment').forEach(segment => {
            segment.addEventListener('click', e => {
                playFromSourceAudio(resultItem.dataset.source, e.target.dataset.start);
            });
        });
    });

    resultItem.dataset.ctxLoaded = '1';
}

/* ========================
   7 ‑ Audio helper to seek header player
   ======================== */
function playFromSourceAudio(sourceId, startSec) {
    const headerAudio = document.querySelector(`.source-header .audio-container[data-source="${encodeURIComponent(sourceId)}"] audio`);
    if (!headerAudio) return;
    audioManager.stop();
    headerAudio.currentTime = parseFloat(startSec);
    headerAudio.play();
}

/* ========================
   8 ‑ Result‑item click binding
   ======================== */
document.addEventListener('DOMContentLoaded', () => {
    // timing logger init
    const rq = document.querySelector('meta[name="request-id"]');
    if (rq) timingLogger.init(rq.content);

    // Load all segments immediately for all result items
    document.querySelectorAll('.result-item').forEach(item => {
        const epi = item.dataset.epi;
        const char = item.dataset.char;
        fetchSegmentByChar(epi, char).then(seg => {
            buildContext(item, seg);
            item.dataset.ctxLoaded = '1';
        });
    });
});

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

function toggleSource(sourceId) {
    const resultsDiv = document.getElementById(sourceId + '-results');
    const icon = document.getElementById('icon-' + sourceId);
    const sourceHeader = document.querySelector(`.source-header[onclick*="${sourceId}"]`);

    if (resultsDiv.style.display === 'none') {
        resultsDiv.style.display = 'block';
        icon.textContent = '▼';

        // Load audio immediately
        const audioContainer = sourceHeader.querySelector('.audio-container');
        if (audioContainer) {
            const srcId = audioContainer.dataset.source;
            const fmt = audioContainer.dataset.format || 'opus';
            const start = parseFloat(audioContainer.dataset.start) || 0;
            const audioUrl = `/audio/${srcId}.${fmt}#t=${start}`;

            const audio = document.createElement('audio');
            audio.controls = true;
            audio.preload = 'metadata';
            const src = document.createElement('source');
            src.src = audioUrl;
            src.type = fmt === 'opus' ? 'audio/ogg; codecs=opus' : fmt === 'mp3' ? 'audio/mpeg' : `audio/${fmt}`;
            audio.appendChild(src);
            audioContainer.appendChild(audio);
            audioManager.register(audio);
        }

        // Ensure header is visible
        if (!isInViewport(sourceHeader)) {
            sourceHeader.scrollIntoView({behavior:'smooth', block:'start'});
        }
    } else {
        resultsDiv.style.display = 'none';
        icon.textContent = '▶';
    }
}
