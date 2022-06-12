from flask import Blueprint, flash, redirect, url_for, render_template, request

from filenavi import model
from .wrap import require_authentication
from .error import AuthenticationFailure, MalformedRequest, Unauthorized

bp = Blueprint("user", __name__)


@bp.route("/<user_name:owner>/")
def profile(owner):
    user = model.User.current()

    return render_template(
        "user/profile.html", user=user, users=model.User.query.all(), owner=owner
    )


@bp.route("/register/", methods=["POST"])
@require_authentication
def register_trampoline():
    user = model.User.current()

    if user.rank < model.Rank.ADMIN:
        raise Unauthorized

    if not all(p in request.form for p in ["name", "password", "rank"]):
        raise MalformedRequest

    if request.form["rank"] not in [r.name for r in model.Rank]:
        raise MalformedRequest

    name = request.form["name"]
    password = request.form["password"]
    rank = model.Rank[request.form["rank"]]

    if rank >= user.rank:
        raise Unauthorized

    if model.User.query.filter_by(name=name).count() > 0:
        flash("User already exists")
        return redirect(url_for(".profile", owner=user))

    new_user = model.User(name, password, rank)

    model.db.session.add(new_user)
    model.db.session.commit()

    return redirect(url_for(".profile", owner=new_user))


@bp.route("/<user_name:owner>/settings/")
@require_authentication
def settings(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    return render_template("user/settings.html", user=user, owner=owner)


@bp.route("/<user_name:owner>/settings/", methods=["POST"])
@require_authentication
def settings_trampoline(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    if user == owner:
        if "password" not in request.form:
            raise AuthenticationFailure
        if not user.verify(request.form["password"]):
            raise AuthenticationFailure

    if "name" in request.form:
        owner.name = request.form["name"]
    if "link-conversion" in request.form:
        if request.form["link-conversion"] not in [
            lc.name for lc in model.LinkConversion
        ]:
            raise MalformedRequest
        owner.link_conversion = model.LinkConversion[request.form["link-conversion"]]
    if "rank" in request.form:
        if user.rank <= owner.rank or user.rank <= model.Rank.ADMIN:
            raise Unauthorized
        if request.form["rank"] not in [r.name for r in model.Rank]:
            raise MalformedRequest
        new_rank = model.Rank[request.form["rank"]]
        if new_rank >= user.rank:
            raise Unauthorized
        owner.rank = new_rank
    model.db.session.commit()
    return redirect(url_for(".profile", owner=owner))


@bp.route("/<user_name:owner>/security/")
@require_authentication
def security(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    return render_template("user/security.html", user=user, owner=owner)


@bp.route("/<user_name:owner>/security/", methods=["POST"])
@require_authentication
def security_trampoline(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    if user == owner:
        if "password" not in request.form:
            raise MalformedRequest
        if not user.verify(request.form["password"]):
            raise AuthenticationFailure

    if not all(p in request.form for p in ["new-password", "re-password"]):
        raise MalformedRequest

    if request.form["new-password"] != request.form["re-password"]:
        flash("Passwords do not match", "error")
        return redirect(url_for(".profile", owner=owner))
    owner.password = request.form["new-password"]
    model.db.session.commit()
    return redirect(url_for(".profile", owner=owner))


@bp.route("/<user_name:owner>/delete/")
@require_authentication
def delete(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    return render_template("user/delete.html", user=user, owner=owner)


@bp.route("/<user_name:owner>/delete/", methods=["POST"])
@require_authentication
def delete_trampoline(owner):
    user = model.User.current()

    if not user.has_access_to(owner):
        raise Unauthorized

    if "name" not in request.form:
        raise MalformedRequest

    if request.form["name"] != owner.name:
        flash("Usernames do not match", "error")
        return redirect(url_for(".profile", owner=owner))

    model.db.session.delete(owner)
    model.db.session.commit()

    if owner == user:
        if "user_id" in session:
            del session["user_id"]

    return redirect(url_for("site.login"))
