# Plex-Movie-Recommendation-Engine
A web application that analyzes your Plex watch history and suggests movies from your library that you're likely to enjoy.

## Stack
|component|technology  |
|--|--|
|backend  | python(flask) |
|plex integration|python-plexapi|
|ML|scikit-learn|
|data handling|Pandas|
|frontend|HTML/CSS, JS|
|Deployment|Docker

## How it works
1. **Load** – every movie in your Plex library is read with python-plexapi (genres, directors,
   actors, studio, year, summary, view count, last viewed date and your star rating) into a
   Pandas DataFrame. The result is cached in memory for `CACHE_TTL` seconds.
2. **Featurize** – each movie becomes one vector made of TF-IDF blocks for genres, directors,
   actors, studio, decade and summary keywords, weighted so genres and people matter most.
3. **Profile** – your taste profile is a weighted average of the movies you've watched:
   - rewatches count more (`1 + ln(views)`),
   - recent watches count more (one-year half-life, never below half weight),
   - a star rating overrides "watched = liked": 5★ pulls hard, 1★ pushes similar movies *away*.
4. **Rank** – unwatched movies are ranked by cosine similarity to the profile. Each pick says
   which watched movies it resembles ("Because you watched …").

With no watch history yet, it falls back to your best audience-rated unwatched movies.

## Running it

### 1. Configure
```bash
cp .env.example .env
```
Set `PLEX_URL`, `PLEX_TOKEN` ([how to find your token](https://support.plex.tv/articles/204059436))
and `PLEX_LIBRARY` (the name of your movie library, default `Movies`).

### 2a. Docker
```bash
docker compose up --build
```
Open http://localhost:8000.

### 2b. Locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python wsgi.py            # dev server on http://localhost:5000
```

## API
| Method | Path | Description |
|--|--|--|
| GET | `/api/recommendations?n=20&genre=&min_year=&max_year=` | Ranked picks with score and reasons |
| GET | `/api/history?n=50` | Watched movies, most recent first |
| GET | `/api/genres` | Genres in your library |
| GET | `/api/stats` | Library and watched counts |
| POST | `/api/refresh` | Reload the library from Plex now |
| GET | `/api/poster/<rating_key>` | Poster image, proxied so your token never reaches the browser |
| GET | `/healthz` | Health check |

## Development
```bash
ruff check . && ruff format --check .
pytest
```
Tests use a fake Plex client and a synthetic library, so no Plex server is needed.

## Project layout
```
app/
  __init__.py      Flask app factory
  config.py        settings from environment variables
  plex_client.py   Plex → DataFrame, poster fetching
  recommender.py   feature building, taste profile, ranking
  service.py       caching layer between Plex and the routes
  routes.py        JSON API and page
  templates/ static/   frontend
tests/
```

## Roadmap
- Multiple Plex users (managed users / Plex Home)
- Recommendations outside your library via TMDB
- Thumbs up/down feedback in the UI to tune the profile
