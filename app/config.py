import os


class Config:
    PLEX_URL = os.environ.get("PLEX_URL", "")
    PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")
    PLEX_LIBRARY = os.environ.get("PLEX_LIBRARY", "Movies")
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "900"))
