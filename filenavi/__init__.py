from pathlib import Path
from urllib.parse import urlparse, urlunparse
from configparser import ConfigParser

from flask import Flask, flash, redirect, url_for, request
from flask_session import Session
from humanfriendly import parse_size
import click

from .routing.conv import VisibilityConverter, UserConverter
from .routing import site, user, storage
from .routing.error import (
    Unauthorized,
    NotAuthenticated,
    AuthenticationFailure,
    MalformedRequest,
    NotAccessible,
)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(SQLALCHEMY_TRACK_MODIFICATIONS=False, SESSION_TYPE="redis")

    user_config = parse_config(app)
    for key in user_config:
        app.config[key] = user_config[key]

    sess = Session()

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.from_mapping(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @app.context_processor
    def inject():
        return {"model": model}

    @app.cli.command("init-db")
    def init_db():
        model.db.create_all()
        owner = model.User("filenavi", "filenavi", model.Rank.OWNER)
        model.db.session.add(owner)
        model.db.session.commit()
        click.echo("Initialized the database")

    app.url_map.converters["user"] = UserConverter
    app.url_map.converters["visibility"] = VisibilityConverter

    app.register_blueprint(site.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(storage.bp)

    def handle_error(error):
        flash(error.message, "error")

        user = model.User.current()
        if user is not None:
            return redirect(
                url_for(
                    "storage.browse", owner=user, visibility=model.Visibility.PRIVATE
                )
            )
        else:
            return redirect(url_for("site.login"))

    app.errorhandler(Unauthorized)(handle_error)
    app.errorhandler(NotAuthenticated)(handle_error)
    app.errorhandler(AuthenticationFailure)(handle_error)
    app.errorhandler(MalformedRequest)(handle_error)
    app.errorhandler(NotAccessible)(handle_error)

    from .model import db

    db.init_app(app)
    sess.init_app(app)

    return app


def parse_config(app):
    basename = "config.ini"

    paths = [Path(Path.cwd().root) / "etc" / "filenavi" / basename, Path(basename)]

    path = None
    for p in paths:
        if p.exists() and p.is_file():
            path = p

    if path is None:
        raise FileNotFoundError("Configuration file is missing")

    config = ConfigParser()
    config.read(path)

    section = None
    for s in config.sections():
        if s == "filenavi":
            section = config[s]
        else:
            raise IndexError("Invalid section")

    assert section is not None

    rv = {
        "SQLALCHEMY_DATABASE_URI": section.get("database_uri"),
        "DATA_DIR": Path(
            section.get("data_dir", str(Path(app.instance_path) / "data"))
        ),
        "USERS_DIR": Path(section.get("users_dir", "users")),
        "MAX_CONTENT_LENGTH": parse_size(section.get("max_content_length", "16MiB")),
    }

    return rv
