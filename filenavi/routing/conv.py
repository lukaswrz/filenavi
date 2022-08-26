from werkzeug.routing import BaseConverter, ValidationError
from urllib.parse import quote
from sqlalchemy.exc import NoResultFound

from filenavi.model import Visibility, User


class UserConverter(BaseConverter):
    def to_python(self, value: str) -> User:
        try:
            user = User.query.filter_by(name=value).one()
        except NoResultFound:
            raise ValidationError

        return user

    def to_url(self, value):
        return quote(value.name)

class VisibilityConverter(BaseConverter):
    def to_python(self, value):
        try:
            for visibility in Visibility:
                if str(visibility) == value:
                    return visibility
        except KeyError:
            raise ValidationError

    def to_url(self, value):
        return quote(str(value))
