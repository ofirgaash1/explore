# app/routes/search.py
from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app, abort

from app.services.search import SearchService, SearchHit
from app.services.index import IndexManager
from app.services.file_service import FileService

bp = Blueprint("search", __name__, url_prefix="/search")


@bp.route("/", methods=["GET"])
def search():
    search_svc = current_app.config["SEARCH_SERVICE"]
    
    q = request.args.get("q", "")
    if not q:
        abort(400, "missing ?q=")
    regex = bool(request.args.get("regex"))
    hits = search_svc.search(q, regex=regex)
    return jsonify([hit.__dict__ for hit in hits])

@bp.route("/snippet", methods=["GET"])
def snippet():
    print("Snippet route called with args:", request.args)
    search_svc = current_app.config["SEARCH_SERVICE"]
    index_mgr = search_svc._index_mgr
    
    try:
        epi = int(request.args["episode_idx"])
        off = int(request.args["offset"])
        size = int(request.args.get("size", 60))
    except (KeyError, ValueError):
        abort(400, "episode_idx, offset (int) required")
    idx = index_mgr.get()
    if epi >= len(idx.text):
        abort(404)
    txt = idx.text[epi]
    return jsonify({"text": txt[max(0, off - 10): off + size]})

@bp.route("/segment", methods=["GET"])
def get_segment():
    print("segment route called with args:", request.args)
    search_svc = current_app.config["SEARCH_SERVICE"]
    try:
        epi  = int(request.args["episode_idx"])
        char = int(request.args["char_offset"])
    except (KeyError, ValueError):
        abort(400, "episode_idx & char_offset (int) are required")

    hit = SearchHit(epi, char)
    seg = search_svc.segment(hit)
    return jsonify({
        "segment_index": seg.seg_idx,
        "start_sec": seg.start_sec,
        "text": seg.text,
    })

@bp.route("/segment/by_idx", methods=["GET"])
def get_segment_by_idx():
    print("segment/by_idx route called with args:", request.args)
    search_svc = current_app.config["SEARCH_SERVICE"]
    try:
        epi  = int(request.args["episode_idx"])
        idx  = int(request.args["seg_idx"])
    except (KeyError, ValueError):
        abort(400, "episode_idx & seg_idx (int) are required")

    seg = search_svc._index_mgr.get()  
    seg = segment_by_idx(seg, epi, idx)
    return jsonify({"segment_index": seg.seg_idx,
                    "start_sec": seg.start_sec,
                    "text": seg.text})