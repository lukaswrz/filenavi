from flask import session, Blueprint, redirect, url_for, render_template, request

from filenavi import model
from .error import AuthenticationFailure, MalformedRequest
from sqlalchemy.exc import NoResultFound

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    user = model.User.current()
    if user is not None:
        return redirect(
            url_for("storage.browse", owner=user, visibility=model.Visibility.PRIVATE)
        )

    return redirect(url_for(".login"))


@bp.route("/login")
def login():
    return render_template("site/login.html")


@bp.route("/login", methods=["POST"])
def login_handler():
    if "user_id" in session:
        del session["user_id"]

    if not all(p in request.form for p in ["name", "password"]):
        raise MalformedRequest

    try:
        user = model.User.query.filter_by(name=request.form.get("name")).one()
    except NoResultFound:
        raise AuthenticationFailure

    if not user.verify(request.form.get("password")):
        raise AuthenticationFailure

    session["user_id"] = user.id
    return redirect(
        url_for("storage.browse", owner=user, visibility=model.Visibility.PRIVATE)
    )


@bp.route("/logout", methods=["POST"])
def logout_handler():
    if "user_id" in session:
        del session["user_id"]
    return redirect(url_for(".login"))
