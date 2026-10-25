import pandas as pd

from app.plex_client import records_to_frame
from app.recommender import Recommender

from .conftest import NOW, library_records, movie


def make(df):
    return Recommender(df, now=pd.Timestamp(NOW))


def titles(recs):
    return [r.title for r in recs]


def test_ranks_similar_movies_first(movies):
    recs = make(movies).recommend(n=10)
    top = titles(recs)
    assert set(top[:3]) == {"Dune", "Inception", "Blade Runner"}
    assert top.index("Pride & Prejudice") > top.index("Blade Runner")


def test_never_recommends_watched(movies):
    recs = make(movies).recommend(n=50)
    assert not {"Arrival", "Interstellar", "The Notebook"} & set(titles(recs))


def test_disliked_movie_pushes_similar_down(movies):
    recs = make(movies).recommend(n=10)
    # Pride & Prejudice resembles the disliked Notebook, so it ranks below an unrelated comedy.
    assert titles(recs).index("Paddington 2") < titles(recs).index("Pride & Prejudice")


def test_shared_director_drives_reason(movies):
    recs = {r.title: r for r in make(movies).recommend(n=10)}
    assert "Arrival" in recs["Dune"].reasons[0]
    assert "Interstellar" in recs["Inception"].reasons[0]
    # Only a shared decade with the watched sci-fi: too weak to claim as a reason.
    assert recs["Paddington 2"].reasons == []


def test_filters(movies):
    rec = make(movies)
    assert titles(rec.recommend(genre="romance")) == ["Pride & Prejudice"]
    assert titles(rec.recommend(min_year=2015)) == ["Dune", "Paddington 2"]
    assert titles(rec.recommend(max_year=1990)) == ["Blade Runner"]
    assert rec.recommend(genre="western") == []


def test_n_limits_results(movies):
    assert len(make(movies).recommend(n=2)) == 2


def test_cold_start_falls_back_to_audience_rating():
    records = [r | {"view_count": 0, "last_viewed_at": None} for r in library_records()]
    recs = make(records_to_frame(records)).recommend(n=3)
    assert titles(recs) == ["Paddington 2", "Inception", "Blade Runner"]
    assert all(r.score == 0 for r in recs)


def test_rewatched_and_recent_movies_weigh_more(movies):
    rec = make(movies)
    w = dict(zip(movies["title"], rec.weights, strict=True))
    assert w["Arrival"] > w["Interstellar"] > 0
    assert w["The Notebook"] < 0
    assert w["Dune"] == 0


def test_handles_missing_metadata():
    df = records_to_frame(
        [
            movie(1, "A", (), None, view_count=1),
            movie(2, "B", (), None),
        ]
    )
    recs = make(df).recommend()
    assert titles(recs) == ["B"]


def test_empty_library():
    assert make(records_to_frame([])).recommend() == []


def test_genres(movies):
    assert make(movies).genres()[:3] == ["Action", "Comedy", "Drama"]
