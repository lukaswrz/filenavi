from re import match

from flask import session
from werkzeug.routing import BaseConverter, ValidationError
from sqlalchemy.exc import NoResultFound

from sfstash import model


class UserIdConverter(BaseConverter):
    def to_python(self, value):
        prefix = "~"
        if value.startswith(prefix):
            try:
                rv = int(value[len(prefix):])
            except ValueError:
                raise ValidationError

            try:
                user = model.User.query.filter_by(id=rv).one()
            except NoResultFound:
                raise ValidationError

            return user

        raise ValidationError

    def to_url(self, value):
        return f"~{value.id}"


class UserNameConverter(BaseConverter):
    def to_python(self, value):
        prefix = "~"
        if value.startswith(prefix):
            try:
                user = model.User.query.filter_by(
                    name=value[len(prefix):]).one()
            except NoResultFound:
                raise ValidationError

            return user

        raise ValidationError

    def to_url(self, value):
        return f"~{value.name}"


class VisibilityConverter(BaseConverter):
    def to_python(self, value):
        try:
            return model.Visibility[value]
        except KeyError:
            raise ValidationError

    def to_url(self, value):
        return str(value)
