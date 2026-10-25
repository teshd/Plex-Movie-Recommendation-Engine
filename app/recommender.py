"""Content-based movie recommender.

Each movie becomes a weighted, L2-normalised feature vector built from its genres,
people, studio, decade and summary. The user's taste profile is a weighted mean of
the vectors of watched movies, and unwatched movies are ranked by cosine similarity
to that profile.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

# Relative importance of each feature block in the combined vector.
BLOCK_WEIGHTS = {
    "genres": 1.0,
    "directors": 0.7,
    "actors": 0.6,
    "studio": 0.2,
    "decade": 0.3,
    "summary": 0.5,
}
RECENCY_HALF_LIFE_DAYS = 365
# A watched movie must be at least this similar to be named as a reason.
REASON_MIN_SIMILARITY = 0.15


def _identity(tokens):
    return tokens


def _list_vectorizer():
    return TfidfVectorizer(analyzer=_identity, lowercase=False)


def _norm_tags(tags):
    return [t.strip().lower() for t in tags if t and t.strip()]


@dataclass
class Recommendation:
    rating_key: int
    title: str
    year: int | None
    genres: list[str]
    summary: str
    score: float
    reasons: list[str] = field(default_factory=list)


class Recommender:
    def __init__(self, movies: pd.DataFrame, now: pd.Timestamp | None = None):
        self.movies = movies.reset_index(drop=True)
        self.now = now or pd.Timestamp.now()
        self.matrix = self._build_matrix(self.movies)
        self.watched_mask = (self.movies["view_count"] > 0).to_numpy()
        self.weights = self._watch_weights(self.movies)
        self.profile = self._build_profile()

    # --- features -------------------------------------------------------

    def _build_matrix(self, df: pd.DataFrame) -> sparse.csr_matrix:
        if df.empty:
            return sparse.csr_matrix((0, 0))
        list_fields = {
            "genres": df["genres"].map(_norm_tags),
            "directors": df["directors"].map(_norm_tags),
            "actors": df["actors"].map(_norm_tags),
            "studio": df["studio"].map(lambda s: _norm_tags([s])),
            "decade": df["year"].map(lambda y: [f"{int(y) // 10 * 10}s"] if pd.notna(y) else []),
        }
        blocks = []
        for name, tokens in list_fields.items():
            block = self._fit_block(_list_vectorizer(), tokens.tolist())
            if block is not None:
                blocks.append(block * BLOCK_WEIGHTS[name])

        summary_vec = TfidfVectorizer(
            stop_words="english", max_features=5000, min_df=2, sublinear_tf=True
        )
        block = self._fit_block(summary_vec, df["summary"].fillna("").tolist())
        if block is not None:
            blocks.append(block * BLOCK_WEIGHTS["summary"])

        if not blocks:
            return sparse.csr_matrix((len(df), 0))
        return normalize(sparse.hstack(blocks).tocsr())

    @staticmethod
    def _fit_block(vectorizer, docs):
        try:
            return normalize(vectorizer.fit_transform(docs))
        except ValueError:  # empty vocabulary (e.g. no summaries at all)
            return None

    # --- taste profile --------------------------------------------------

    def _watch_weights(self, df: pd.DataFrame) -> np.ndarray:
        """How strongly each watched movie should pull the profile (negative = push away)."""
        weights = np.zeros(len(df))
        for i, row in df.iterrows():
            if row["view_count"] <= 0:
                continue
            # Rewatches signal stronger preference, with diminishing returns.
            w = 1.0 + np.log(row["view_count"])
            # Recent watches count more than old ones, but never less than half.
            if pd.notna(row["last_viewed_at"]):
                days = max((self.now - row["last_viewed_at"]).days, 0)
                w *= 0.5 + 0.5 * 0.5 ** (days / RECENCY_HALF_LIFE_DAYS)
            # An explicit star rating (0-10) overrides the "watched = liked" assumption.
            rating = row["user_rating"]
            if pd.notna(rating):
                w *= (float(rating) - 5.0) / 5.0
            weights[i] = w
        return weights

    def _build_profile(self) -> np.ndarray | None:
        if not self.weights.any() or self.matrix.shape[1] == 0:
            return None
        profile = self.matrix.T @ self.weights / np.abs(self.weights).sum()
        norm = np.linalg.norm(profile)
        if norm == 0 or (self.matrix @ profile).max() <= 0:
            return None
        return profile / norm

    # --- ranking --------------------------------------------------------

    def recommend(
        self,
        n: int = 20,
        genre: str | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
    ) -> list[Recommendation]:
        if self.movies.empty:
            return []
        candidates = ~self.watched_mask
        if genre:
            g = genre.strip().lower()
            candidates &= self.movies["genres"].map(lambda gs: g in _norm_tags(gs)).to_numpy()
        years = self.movies["year"]
        if min_year is not None:
            candidates &= (years >= min_year).fillna(False).to_numpy()
        if max_year is not None:
            candidates &= (years <= max_year).fillna(False).to_numpy()

        idx = np.flatnonzero(candidates)
        if idx.size == 0:
            return []

        if self.profile is None:
            return self._fallback(idx, n)

        scores = self.matrix[idx] @ self.profile
        order = idx[np.argsort(-scores, kind="stable")][:n]
        score_by_idx = dict(zip(idx, scores, strict=True))
        return [self._make(i, float(score_by_idx[i]), self._reasons(i)) for i in order]

    def _fallback(self, idx: np.ndarray, n: int) -> list[Recommendation]:
        """No usable watch history: suggest the best audience-rated unwatched movies."""
        ratings = self.movies.loc[idx, "audience_rating"].fillna(0).to_numpy()
        order = idx[np.argsort(-ratings, kind="stable")][:n]
        reason = ["Highly rated in your library (watch a few movies for personal picks)"]
        return [self._make(i, 0.0, reason) for i in order]

    def _reasons(self, i: int, top: int = 3) -> list[str]:
        """Name the watched movies that contributed most to this recommendation."""
        liked = np.flatnonzero(self.weights > 0)
        if liked.size == 0:
            return []
        sims = (self.matrix[liked] @ self.matrix[i].T).toarray().ravel()
        contrib = sims * self.weights[liked]
        best = [liked[j] for j in np.argsort(-contrib)[:top] if sims[j] >= REASON_MIN_SIMILARITY]
        if not best:
            return []
        titles = ", ".join(self.movies.at[j, "title"] for j in best)
        return [f"Because you watched {titles}"]

    def _make(self, i: int, score: float, reasons: list[str]) -> Recommendation:
        row = self.movies.iloc[i]
        return Recommendation(
            rating_key=int(row["rating_key"]),
            title=row["title"],
            year=int(row["year"]) if pd.notna(row["year"]) else None,
            genres=list(row["genres"]),
            summary=row["summary"],
            score=round(score, 4),
            reasons=reasons,
        )

    def genres(self) -> list[str]:
        return sorted({g for gs in self.movies["genres"] for g in gs})
