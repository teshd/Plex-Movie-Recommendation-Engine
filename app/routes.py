from dataclasses import asdict

from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

bp = Blueprint("main", __name__)


def _library():
    return current_app.extensions["library"]


def _int_arg(name, default=None, lo=None, hi=None):
    raw = request.args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        abort(400, description=f"'{name}' must be an integer")
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


@bp.errorhandler(400)
def bad_request(err):
    return jsonify(error=err.description), 400


@bp.errorhandler(Exception)
def unexpected_error(err):
    if isinstance(err, HTTPException):
        return err
    current_app.logger.exception("Request failed")
    return jsonify(error=f"Could not load data from Plex: {err}"), 502


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@bp.get("/api/recommendations")
def recommendations():
    recs = _library().recommender.recommend(
        n=_int_arg("n", 20, lo=1, hi=100),
        genre=request.args.get("genre") or None,
        min_year=_int_arg("min_year"),
        max_year=_int_arg("max_year"),
    )
    items = []
    for rec in recs:
        item = asdict(rec)
        item["poster"] = f"/api/poster/{rec.rating_key}"
        items.append(item)
    return jsonify(recommendations=items)


@bp.get("/api/history")
def history():
    return jsonify(history=_library().history(n=_int_arg("n", 50, lo=1, hi=500)))


@bp.get("/api/genres")
def genres():
    return jsonify(genres=_library().recommender.genres())


@bp.get("/api/stats")
def stats():
    return jsonify(_library().stats())


@bp.post("/api/refresh")
def refresh():
    library = _library()
    library.refresh()
    return jsonify(library.stats())


@bp.get("/api/poster/<int:rating_key>")
def poster(rating_key):
    library = _library()
    thumb = library.thumb_for(rating_key)
    if not thumb:
        abort(404)
    try:
        data, content_type = library.client.fetch_image(thumb)
    except Exception:
        current_app.logger.exception("Failed to fetch poster %s", rating_key)
        abort(502)
    return Response(data, mimetype=content_type, headers={"Cache-Control": "max-age=86400"})
