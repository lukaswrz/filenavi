import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from configparser import ConfigParser

from flask import Flask, session, flash, redirect, url_for, request
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
from humanfriendly import parse_size
import click

from . import model
from .routing.conv import (
    UserIdConverter,
    UserNameConverter,
    VisibilityConverter)
from .routing import site, user, storage
from .routing.error import (
    Unauthorized,
    NotAuthenticated,
    AuthenticationFailure,
    MalformedRequest,
    NotAccessible)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_TYPE="redis")

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
        return {
            "icon": app.config["ICON_URL"],
            "model": model
        }

    @app.cli.command("init-db")
    def init_db():
        model.db.create_all()
        owner = model.User("sfstash", "sfstash", model.Rank.OWNER)
        model.db.session.add(owner)
        model.db.session.commit()
        click.echo("Initialized the database")

    app.url_map.converters["user_id"] = UserIdConverter
    app.url_map.converters["user_name"] = UserNameConverter
    app.url_map.converters["visibility"] = VisibilityConverter

    app.register_blueprint(site.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(storage.bp)

    # expand ~ and user ids to ~user
    @app.route("/~/")
    @app.route("/~/<path:path>")
    @app.route("/id/~/")
    @app.route("/id/~/<path:path>")
    @app.route("/id/<user_id:owner>/")
    @app.route("/id/<user_id:owner>/<path:path>")
    def expand(owner=None, path=""):
        if owner is not None:
            new_path = f"/~{owner.name}/{path}"
        else:
            user = model.User.current()
            if user is None:
                raise NotAuthenticated
            new_path = f"/~{user.name}/{path}"

        current_url = urlparse(request.url)
        new_url = urlunparse(current_url._replace(path=new_path))
        return redirect(new_url)

    @app.errorhandler(Unauthorized)
    @app.errorhandler(NotAuthenticated)
    @app.errorhandler(AuthenticationFailure)
    @app.errorhandler(MalformedRequest)
    @app.errorhandler(NotAccessible)
    def handle_error(error):
        flash(error.message, "error")

        user = model.User.current()
        if user is not None:
            return redirect(
                url_for(
                    "storage.main",
                    owner=user,
                    visibility=model.Visibility.private))
        else:
            return redirect(url_for("site.login"))

    from .model import db
    db.init_app(app)
    sess.init_app(app)

    return app


def parse_config(app):
    basename = "config.ini"

    paths = [
        Path.home() / ".config" / "sfstash" / basename,
        Path("/etc") / "sfstash" / basename,
    ]

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", None)
    if xdg_config_home is not None:
        paths.insert(0, Path(xdg_config_home) / "sfstash" / basename)

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
        if s == "sfstash":
            section = config[s]
        else:
            raise IndexError("Invalid section")

    rv = {
        "SQLALCHEMY_DATABASE_URI": section.get("database_uri"),
        "DATA_DIR": section.get("data_dir", Path(app.instance_path) / "data"),
        "USERS_DIR": section.get("users_dir", Path("users")),
        "ICON_URL": section.get("icon_url", None),
        "MAX_CONTENT_LENGTH": parse_size(section.get("max_content_length")),
    }

    return rv
