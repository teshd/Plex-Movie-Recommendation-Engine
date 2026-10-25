"""Caches the Plex library and the fitted recommender between requests."""

import threading
import time

import pandas as pd

from .recommender import Recommender


class LibraryService:
    def __init__(self, client, ttl: int = 900):
        self.client = client
        self.ttl = ttl
        self._lock = threading.Lock()
        self._movies: pd.DataFrame | None = None
        self._recommender: Recommender | None = None
        self._loaded_at = 0.0

    def _stale(self) -> bool:
        return self._movies is None or time.monotonic() - self._loaded_at > self.ttl

    def refresh(self) -> None:
        movies = self.client.load_movies()
        recommender = Recommender(movies)
        with self._lock:
            self._movies, self._recommender = movies, recommender
            self._loaded_at = time.monotonic()

    def _ensure(self) -> None:
        if self._stale():
            self.refresh()

    @property
    def recommender(self) -> Recommender:
        self._ensure()
        return self._recommender

    @property
    def movies(self) -> pd.DataFrame:
        self._ensure()
        return self._movies

    def history(self, n: int = 50) -> list[dict]:
        df = self.movies
        watched = df[df["view_count"] > 0].sort_values(
            "last_viewed_at", ascending=False, na_position="last"
        )
        out = []
        for row in watched.head(n).itertuples():
            out.append(
                {
                    "rating_key": int(row.rating_key),
                    "title": row.title,
                    "year": int(row.year) if pd.notna(row.year) else None,
                    "view_count": int(row.view_count),
                    "last_viewed_at": row.last_viewed_at.isoformat()
                    if pd.notna(row.last_viewed_at)
                    else None,
                    "user_rating": float(row.user_rating) if pd.notna(row.user_rating) else None,
                }
            )
        return out

    def thumb_for(self, rating_key: int) -> str | None:
        match = self.movies.loc[self.movies["rating_key"] == rating_key, "thumb"]
        if match.empty:
            return None
        return match.iloc[0] or None

    def stats(self) -> dict:
        df = self.movies
        return {"total": len(df), "watched": int((df["view_count"] > 0).sum())}
