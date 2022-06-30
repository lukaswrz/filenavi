from werkzeug.routing import BaseConverter, ValidationError
from urllib.parse import quote
from sqlalchemy.exc import NoResultFound

from filenavi.model import Visibility, Identifier, User


class UserConverter(BaseConverter):
    def __init__(
        self,
        map: "Map",
        identifier: str
    ) -> None:
        super().__init__(map)
        self.identifier = Identifier[identifier]
        self.prefixes: dict[Identifier, str] = {
            Identifier.ID: '#',
            Identifier.NAME: '~'
        }

    def to_python(self, value: str) -> User:
        if value.startswith(self.prefixes[self.identifier]):
            try:
                match self.identifier:
                    case Identifier.ID:
                        try:
                            id = int(value[len(self.prefixes[self.identifier]): ])
                        except ValueError:
                            raise ValidationError

                        user = User.query.filter_by(id=id).one()
                    case Identifier.NAME:
                        user = User.query.filter_by(name=value[len(self.prefixes[self.identifier]) :]).one()
            except NoResultFound:
                raise ValidationError

            return user

        raise ValidationError

    def to_url(self, value):
        return quote(f"{self.prefixes[self.identifier]}{value.name}")

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
