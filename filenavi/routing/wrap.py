from functools import wraps
from enum import Enum

from flask import session, request

from filenavi import model
from .error import Unauthorized, NotAuthenticated, MalformedRequest


def require_authentication(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if model.User.current() is None:
            raise NotAuthenticated
        return f(*args, **kwargs)

    return wrap
