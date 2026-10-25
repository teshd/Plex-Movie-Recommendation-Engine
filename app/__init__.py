from flask import Flask

from .config import Config


def create_app(client=None, config: dict | None = None) -> Flask:
    """Build the app. Pass ``client`` (anything with load_movies/fetch_image) to skip Plex."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    if client is None:
        from .plex_client import PlexClient

        client = PlexClient(
            app.config["PLEX_URL"], app.config["PLEX_TOKEN"], app.config["PLEX_LIBRARY"]
        )

    from .routes import bp
    from .service import LibraryService

    app.extensions["library"] = LibraryService(client, ttl=app.config["CACHE_TTL"])
    app.register_blueprint(bp)
    return app
