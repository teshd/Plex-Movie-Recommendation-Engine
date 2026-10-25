"""Thin wrapper around python-plexapi that returns the movie library as a DataFrame."""

from datetime import datetime

import pandas as pd

COLUMNS = [
    "rating_key",
    "title",
    "year",
    "genres",
    "directors",
    "actors",
    "studio",
    "summary",
    "content_rating",
    "audience_rating",
    "view_count",
    "last_viewed_at",
    "user_rating",
    "thumb",
]


def _tags(items):
    return [t.tag for t in (items or []) if getattr(t, "tag", None)]


def movie_to_record(movie) -> dict:
    """Convert a plexapi Movie into a flat dict, without triggering a per-item reload."""
    movie._autoReload = False
    last_viewed = movie.lastViewedAt
    return {
        "rating_key": int(movie.ratingKey),
        "title": movie.title,
        "year": movie.year,
        "genres": _tags(movie.genres),
        "directors": _tags(movie.directors),
        "actors": _tags(movie.roles),
        "studio": movie.studio or "",
        "summary": movie.summary or "",
        "content_rating": movie.contentRating or "",
        "audience_rating": movie.audienceRating,
        "view_count": movie.viewCount or 0,
        "last_viewed_at": last_viewed if isinstance(last_viewed, datetime) else None,
        "user_rating": movie.userRating,
        "thumb": movie.thumb or "",
    }


def records_to_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records, columns=COLUMNS)
    df["last_viewed_at"] = pd.to_datetime(df["last_viewed_at"])
    df["view_count"] = df["view_count"].fillna(0).astype(int)
    return df


class PlexClient:
    def __init__(self, url: str, token: str, library: str):
        self.url = url
        self.token = token
        self.library = library
        self._server = None

    @property
    def server(self):
        if self._server is None:
            if not self.url or not self.token:
                raise ValueError("PLEX_URL and PLEX_TOKEN must be set")
            from plexapi.server import PlexServer

            self._server = PlexServer(self.url, self.token)
        return self._server

    def load_movies(self) -> pd.DataFrame:
        section = self.server.library.section(self.library)
        return records_to_frame([movie_to_record(m) for m in section.all()])

    def fetch_image(self, path: str) -> tuple[bytes, str]:
        """Fetch a poster from Plex so the token never reaches the browser."""
        resp = self.server._session.get(
            self.server.url(path), headers={"X-Plex-Token": self.token}, timeout=15
        )
        resp.raise_for_status()
        return resp.content, resp.headers.get("Content-Type", "image/jpeg")
