"""MSTracker application factory; importing this module starts no processes."""
from datetime import timedelta
from pathlib import Path

from flask import Flask

from .db import opened, instance, migrate

__version__ = "0.1.0"


def create_app(data_dir, test_config=None):
    database = Path(data_dir).resolve() / "mstracker.sqlite3"
    if not database.is_file():
        raise ValueError("No database found. Run setup first with this data directory.")
    with opened(database) as db:
        migrate(db)
        settings = dict(instance(db))
    app = Flask(__name__)
    app.config.update(
        DATABASE=database, INSTRUMENT=settings, SECRET_KEY=settings["secret_key"],
        SESSION_COOKIE_NAME="mstracker_" + settings["id"],
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_REFRESH_EACH_REQUEST=False, MAX_CONTENT_LENGTH=65536,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
    )
    if test_config:
        app.config.update(test_config)
    from .web import bp, close_db
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)
    return app
