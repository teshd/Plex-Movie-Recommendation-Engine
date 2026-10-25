def test_index(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Plex Picks" in res.data


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_recommendations(client):
    data = client.get("/api/recommendations?n=3").get_json()["recommendations"]
    assert len(data) == 3
    first = data[0]
    assert {"title", "year", "genres", "score", "reasons", "poster"} <= first.keys()
    assert first["poster"] == f"/api/poster/{first['rating_key']}"


def test_recommendations_filters(client):
    data = client.get("/api/recommendations?genre=Romance").get_json()["recommendations"]
    assert [d["title"] for d in data] == ["Pride & Prejudice"]


def test_bad_int_param(client):
    res = client.get("/api/recommendations?min_year=abc")
    assert res.status_code == 400
    assert "min_year" in res.get_json()["error"]


def test_history_sorted_by_recency(client):
    hist = client.get("/api/history").get_json()["history"]
    assert [h["title"] for h in hist] == ["The Notebook", "Arrival", "Interstellar"]


def test_genres_and_stats(client):
    assert "Science Fiction" in client.get("/api/genres").get_json()["genres"]
    assert client.get("/api/stats").get_json() == {"total": 8, "watched": 3}


def test_library_is_cached_until_refresh(client, fake_client):
    client.get("/api/stats")
    client.get("/api/recommendations")
    assert fake_client.loads == 1
    assert client.post("/api/refresh").status_code == 200
    assert fake_client.loads == 2


def test_poster_proxy(client):
    res = client.get("/api/poster/10")
    assert res.status_code == 200
    assert res.mimetype == "image/png"
    assert client.get("/api/poster/9999").status_code == 404


def test_plex_failure_returns_json_error(fake_client):
    from app import create_app

    def boom():
        raise ConnectionError("server unreachable")

    fake_client.load_movies = boom
    client = create_app(client=fake_client).test_client()
    res = client.get("/api/stats")
    assert res.status_code == 502
    assert "server unreachable" in res.get_json()["error"]
