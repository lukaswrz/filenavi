from flask import (
    Blueprint,
    flash,
    redirect,
    url_for,
    render_template,
    request,
    send_from_directory,
)

from filenavi import model
from .wrap import require_authentication
from .error import MalformedRequest, Unauthorized, NotAuthenticated, NotAccessible

INLINE_EXTENSIONS = ["txt", "pdf", "png", "jpg", "jpeg", "gif"]

bp = Blueprint("storage", __name__)


@bp.route("/id/<user_id:owner>/storage/<visibility:visibility>/main/")
@bp.route("/id/<user_id:owner>/storage/<visibility:visibility>/main/<path:path>")
def main_id(owner, visibility, path=None):
    return redirect(url_for(".main", owner=owner, visibility=visibility, path=path))


@bp.route("/<user_name:owner>/storage/<visibility:visibility>/main/")
@bp.route("/<user_name:owner>/storage/<visibility:visibility>/main/<path:path>")
def main(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home
    target = model.File(path, owner, visibility)

    if visibility == model.Visibility.private:
        if user is None:
            raise NotAuthenticated
        if not user.has_access_to(target):
            raise Unauthorized

    if not path.is_dir():
        as_attachment = True
        if any(str(target.path).lower().endswith(f".{e}") for e in INLINE_EXTENSIONS):
            as_attachment = False
        return send_from_directory(
            home, target.path.relative_to(home), as_attachment=as_attachment
        )

    if user is None or not user.has_access_to(target):
        raise Unauthorized

    if not request.path.endswith("/"):
        return redirect(f"{request.url}/")

    files = []
    try:
        for f in path.iterdir():
            f = f.relative_to(home)

            files.append(model.File(f, owner, visibility))
    except:
        raise NotAccessible

    parent = None
    if not home.resolve() == path.resolve():
        parent = ".."

    return render_template(
        "storage/main.html",
        files=files,
        user=user,
        owner=owner,
        visibility=visibility,
        current=path.relative_to(home) if path != home else "",
        parent=parent,
    )


@bp.route("/<user_name:owner>/storage/<visibility:visibility>/main/", methods=["POST"])
@bp.route(
    "/<user_name:owner>/storage/<visibility:visibility>/main/<path:path>",
    methods=["POST"],
)
@require_authentication
def main_trampoline(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home
    target = model.File(path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    if "files" in request.files:
        uploads = request.files.getlist("files")
        for upload in uploads:
            if upload.filename == "":
                raise MalformedRequest
            upload.save(path / upload.filename)
    if "directory" in request.form:
        if request.form["directory"] == "":
            raise MalformedRequest
        directory = model.File(path / request.form["directory"], owner, visibility)
        directory.mkdir()
    return redirect(
        url_for(
            ".main", visibility=visibility, path=path.relative_to(home), owner=owner
        )
    )


@bp.route("/<user_name:owner>/storage/<visibility:visibility>/settings/<path:path>")
@require_authentication
def settings(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    return render_template(
        "storage/settings.html",
        file=target,
        user=user,
        owner=owner,
        visibility=visibility,
    )


@bp.route(
    "/<user_name:owner>/storage/<visibility:visibility>/settings/<path:path>",
    methods=["POST"],
)
@require_authentication
def settings_trampoline(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(home / path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    rv = redirect(
        url_for(
            ".main",
            visibility=visibility,
            path=path.relative_to(home).parents[0],
            owner=owner,
        )
    )

    if "move-path" in request.form:
        if not target.path.exists():
            flash("No such file or directory", "error")
            return rv

        try:
            force = "replace" in request.form
            target.move(home / request.form["move-path"], force=force)
        except ValueError:
            flash("Unable to move file", "error")
            return rv
        return rv
    if "toggle-path" in request.form:
        try:
            force = "replace" in request.form
            target.toggle(request.form["toggle-path"], force=force)
        except ValueError:
            flash("Cannot toggle visibility", "error")
            return rv
        return rv
    if "remove" in request.form:
        recursive = "recursive" in request.form
        try:
            target.remove(recursive=recursive)
        except ValueError:
            flash("No such file or directory", "error")
            return rv
        except OSError:
            flash("Cannot remove file or directory", "error")
            return rv
        return rv

    raise MalformedRequest
