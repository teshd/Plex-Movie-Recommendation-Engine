from datetime import datetime, timedelta

import pytest

from app import create_app
from app.plex_client import records_to_frame

NOW = datetime(2026, 1, 1)


def movie(key, title, genres, year=2000, directors=(), actors=(), summary="", **kw):
    return {
        "rating_key": key,
        "title": title,
        "year": year,
        "genres": list(genres),
        "directors": list(directors),
        "actors": list(actors),
        "studio": kw.get("studio", ""),
        "summary": summary,
        "content_rating": "",
        "audience_rating": kw.get("audience_rating"),
        "view_count": kw.get("view_count", 0),
        "last_viewed_at": kw.get("last_viewed_at"),
        "user_rating": kw.get("user_rating"),
        "thumb": kw.get("thumb", f"/library/metadata/{key}/thumb"),
    }


def library_records():
    sci_fi = ("Science Fiction", "Action")
    return [
        # Watched: the user loves sci-fi by Villeneuve / Nolan.
        movie(
            1,
            "Arrival",
            sci_fi,
            2016,
            ["Denis Villeneuve"],
            ["Amy Adams"],
            "Linguist decodes alien language spaceship contact",
            view_count=2,
            last_viewed_at=NOW - timedelta(days=10),
        ),
        movie(
            2,
            "Interstellar",
            sci_fi,
            2014,
            ["Christopher Nolan"],
            ["Matthew McConaughey"],
            "Astronauts travel through wormhole space time",
            view_count=1,
            last_viewed_at=NOW - timedelta(days=30),
        ),
        # Watched but disliked.
        movie(
            3,
            "The Notebook",
            ("Romance", "Drama"),
            2004,
            ["Nick Cassavetes"],
            ["Ryan Gosling"],
            "Love story summer romance",
            view_count=1,
            last_viewed_at=NOW - timedelta(days=5),
            user_rating=1.0,
        ),
        # Unwatched candidates.
        movie(
            10,
            "Dune",
            sci_fi,
            2021,
            ["Denis Villeneuve"],
            ["Timothée Chalamet"],
            "Desert planet space spice empire",
            audience_rating=8.0,
        ),
        movie(
            11,
            "Inception",
            sci_fi,
            2010,
            ["Christopher Nolan"],
            ["Leonardo DiCaprio"],
            "Dream heist time layers",
            audience_rating=8.5,
        ),
        movie(
            12,
            "Pride & Prejudice",
            ("Romance", "Drama"),
            2005,
            ["Joe Wright"],
            ["Keira Knightley"],
            "Love story romance estate",
            audience_rating=7.8,
        ),
        movie(
            13,
            "Paddington 2",
            ("Comedy", "Family"),
            2017,
            ["Paul King"],
            ["Ben Whishaw"],
            "Bear marmalade prison",
            audience_rating=9.0,
        ),
        movie(
            14,
            "Blade Runner",
            sci_fi,
            1982,
            ["Ridley Scott"],
            ["Harrison Ford"],
            "Replicants future space android",
            audience_rating=8.1,
        ),
    ]


@pytest.fixture
def movies():
    return records_to_frame(library_records())


class FakeClient:
    def __init__(self, records):
        self.records = records
        self.loads = 0

    def load_movies(self):
        self.loads += 1
        return records_to_frame(self.records)

    def fetch_image(self, path):
        return b"\x89PNG fake", "image/png"


@pytest.fixture
def fake_client():
    return FakeClient(library_records())


@pytest.fixture
def client(fake_client):
    app = create_app(client=fake_client, config={"TESTING": True})
    return app.test_client()
