from datetime import datetime
from types import SimpleNamespace

import pytest

from app.plex_client import PlexClient, movie_to_record


def tag(name):
    return SimpleNamespace(tag=name)


def test_movie_to_record_flattens_tags():
    m = SimpleNamespace(
        ratingKey="42",
        title="Heat",
        year=1995,
        genres=[tag("Crime"), tag("Thriller")],
        directors=[tag("Michael Mann")],
        roles=[tag("Al Pacino"), tag("Robert De Niro")],
        studio="Warner",
        summary="Cops",
        contentRating="R",
        audienceRating=8.3,
        viewCount=3,
        lastViewedAt=datetime(2025, 5, 1),
        userRating=None,
        thumb="/thumb/42",
    )
    rec = movie_to_record(m)
    assert m._autoReload is False
    assert rec["rating_key"] == 42
    assert rec["genres"] == ["Crime", "Thriller"]
    assert rec["actors"] == ["Al Pacino", "Robert De Niro"]
    assert rec["view_count"] == 3


def test_movie_to_record_handles_missing_fields():
    m = SimpleNamespace(
        ratingKey=1,
        title="X",
        year=None,
        genres=None,
        directors=[],
        roles=None,
        studio=None,
        summary=None,
        contentRating=None,
        audienceRating=None,
        viewCount=None,
        lastViewedAt=None,
        userRating=None,
        thumb=None,
    )
    rec = movie_to_record(m)
    assert rec["genres"] == [] and rec["summary"] == "" and rec["view_count"] == 0


def test_client_requires_credentials():
    client = PlexClient("", "", "Movies")  # constructing is fine so the app can start
    with pytest.raises(ValueError, match="PLEX_URL"):
        client.load_movies()
