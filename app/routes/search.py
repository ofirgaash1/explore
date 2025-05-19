# app/routes/search.py
from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app, abort

from app.services.search import SearchService
from app.services.index import IndexManager
from app.services.file_service import FileService

bp = Blueprint("search", __name__, url_prefix="/search")

# singletons created at import-time
_file_svc  = FileService(current_app.config["TRANSCRIPTS_DIR"])
_index_mgr = IndexManager(_file_svc)
_search_svc = SearchService(_index_mgr)


@bp.route("/", methods=["GET"])
def search():
    q = request.args.get("q", "")
    if not q:
        abort(400, "missing ?q=")
    regex = bool(request.args.get("regex"))
    hits = _search_svc.search(q, regex=regex)
    return jsonify([hit.__dict__ for hit in hits])


@bp.route("/snippet", methods=["GET"])
def snippet():
    try:
        epi = int(request.args["episode_idx"])
        off = int(request.args["offset"])
        size = int(request.args.get("size", 60))
    except (KeyError, ValueError):
        abort(400, "episode_idx, offset (int) required")
    idx = _index_mgr.get()
    if epi >= len(idx.text):
        abort(404)
    txt = idx.text[epi]
    return jsonify({"text": txt[max(0, off - 10): off + size]})
