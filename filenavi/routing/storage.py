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


@bp.route("/<user_id:owner>/<visibility:visibility>/browse/")
@bp.route("/<user_id:owner>/<visibility:visibility>/browse/<path:path>")
def browse_id(owner, visibility, path=None):
    return redirect(url_for(".browse", owner=owner, visibility=visibility, path=path))


@bp.route("/<user_name:owner>/<visibility:visibility>/browse/")
@bp.route("/<user_name:owner>/<visibility:visibility>/browse/<path:path>")
def browse(owner, visibility, path=None):
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
    if not home.samefile(path):
        parent = model.File(path.parent, owner, visibility)

    return render_template(
        "storage/browse.html",
        files=files,
        user=user,
        owner=owner,
        visibility=visibility,
        current=path.relative_to(home) if path != home else "",
        parent=parent,
    )


@bp.route("/<user_name:owner>/<visibility:visibility>/browse/", methods=["POST"])
@bp.route(
    "/<user_name:owner>/<visibility:visibility>/browse/<path:path>", methods=["POST"]
)
@require_authentication
def browse_handler(owner, visibility, path=None):
    user = model.User.current()

    if "files" not in request.files and "directory" not in request.form:
        raise MalformedRequest

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
            ".browse", visibility=visibility, path=path.relative_to(home), owner=owner
        )
    )


@bp.route("/<user_name:owner>/<visibility:visibility>/move/<path:path>")
@require_authentication
def move(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    return render_template(
        "storage/move.html",
        file=target,
        user=user,
        owner=owner,
        visibility=visibility,
    )


@bp.route(
    "/<user_name:owner>/<visibility:visibility>/move/<path:path>",
    methods=["POST"],
)
@require_authentication
def move_handler(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(home / path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    rv = redirect(
        url_for(
            ".browse",
            visibility=visibility,
            path=path.relative_to(home).parents[0],
            owner=owner,
        )
    )

    if "path" not in request.form:
        raise MalformedRequest

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


@bp.route("/<user_name:owner>/<visibility:visibility>/toggle/<path:path>")
@require_authentication
def toggle(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    return render_template(
        "storage/toggle.html",
        file=target,
        user=user,
        owner=owner,
        visibility=visibility,
    )


@bp.route(
    "/<user_name:owner>/<visibility:visibility>/toggle/<path:path>",
    methods=["POST"],
)
@require_authentication
def toggle_handler(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(home / path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    rv = redirect(
        url_for(
            ".browse",
            visibility=visibility,
            path=path.relative_to(home).parents[0],
            owner=owner,
        )
    )

    if "path" not in request.form:
        raise MalformedRequest

    try:
        force = "replace" in request.form
        # TODO: Do not require a Path object
        from pathlib import Path

        target.toggle(Path(request.form["path"]), force=force)
    except ValueError:
        flash("Cannot toggle visibility", "error")
        return rv
    return rv


@bp.route("/<user_name:owner>/<visibility:visibility>/remove/<path:path>")
@require_authentication
def remove(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    return render_template(
        "storage/remove.html",
        file=target,
        user=user,
        owner=owner,
        visibility=visibility,
    )


@bp.route(
    "/<user_name:owner>/<visibility:visibility>/remove/<path:path>",
    methods=["POST"],
)
@require_authentication
def remove_handler(owner, visibility, path=None):
    user = model.User.current()

    home = owner.home(visibility)
    path = (home / path) if path is not None else home

    target = model.File(home / path, owner, visibility)

    if not user.has_access_to(target):
        raise Unauthorized

    rv = redirect(
        url_for(
            ".browse",
            visibility=visibility,
            path=path.relative_to(home).parents[0],
            owner=owner,
        )
    )

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
