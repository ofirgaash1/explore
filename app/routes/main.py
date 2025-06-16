from flask import Blueprint, render_template, request, jsonify, current_app
from ..services.search import SearchService
from ..services.file_service import FileService
from ..services.analytics_service import track_performance
from ..routes.auth import login_required
import time
import os
import logging
import uuid
from ..services.index import IndexManager

logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

# Global search service instance for persistence
search_service = None
file_service = None

@bp.route('/')
@login_required
def home():
    # Track page view
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_event('page_viewed', {'page': 'home'})
    return render_template('home.html')

@bp.route('/search')
@login_required
@track_performance('search_executed', include_args=['query', 'regex', 'page'])
def search():
    query      = request.args.get('q', '').strip()
    use_regex  = request.args.get('regex', '').lower() in ('true', '1', 'on')
    per_page   = int(request.args.get('max_results', 100))
    page       = max(1, int(request.args.get('page', 1)))

    global search_service, file_service
    if file_service is None:
        file_service = FileService(current_app)
    if search_service is None:
        search_service = SearchService(IndexManager(file_service))

    hits = search_service.search(query, regex=use_regex)
    total = len(hits)

    # simple slicing
    start_i = (page - 1) * per_page
    end_i   = start_i + per_page
    page_hits = hits[start_i:end_i]

    # enrich hits with segment info (start time + index)
    records = []
    for h in page_hits:
        seg = search_service.segment(h)
        records.append({
            "episode_idx":  h.episode_idx,
            "char_offset":  h.char_offset,
            "recording_id": search_service._index_mgr.get().ids[h.episode_idx],
            "source":       search_service._index_mgr.get().ids[h.episode_idx],
            "segment_idx":  seg.seg_idx,
            "start_sec":    seg.start_sec,
        })

    pagination = {
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "total_results": total,
        "has_prev": page > 1,
        "has_next": end_i < total,
    }

    if request.headers.get('Accept') == 'application/json':
        return jsonify({"results": records, "pagination": pagination})

    return render_template('results.html',
                           query=query,
                           results=records,
                           pagination=pagination,
                           regex=use_regex,
                           max_results=per_page)

@bp.route('/privacy')
def privacy_policy():
    # Track page view
    analytics = current_app.config.get('ANALYTICS_SERVICE')
    if analytics:
        analytics.capture_event('page_viewed', {'page': 'privacy_policy'})
    return render_template('privacy.html') 