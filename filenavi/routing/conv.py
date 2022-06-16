from werkzeug.routing import BaseConverter, ValidationError
from sqlalchemy.exc import NoResultFound
from urllib.parse import quote

from filenavi import model


class UserIdConverter(BaseConverter):
    prefix = "#"

    def to_python(self, value):
        if value.startswith(self.prefix):
            try:
                rv = int(value[len(self.prefix) :])
            except ValueError:
                raise ValidationError

            try:
                user = model.User.query.filter_by(id=rv).one()
            except NoResultFound:
                raise ValidationError

            return user

        raise ValidationError

    def to_url(self, value):
        return quote(f"{self.prefix}{value.id}")


class UserNameConverter(BaseConverter):
    prefix = "~"

    def to_python(self, value):
        if value.startswith(self.prefix):
            try:
                user = model.User.query.filter_by(name=value[len(self.prefix) :]).one()
            except NoResultFound:
                raise ValidationError

            return user

        raise ValidationError

    def to_url(self, value):
        return quote(f"{self.prefix}{value.name}")


class VisibilityConverter(BaseConverter):
    def to_python(self, value):
        try:
            return model.Visibility[value]
        except KeyError:
            raise ValidationError

    def to_url(self, value):
        return quote(str(value))
