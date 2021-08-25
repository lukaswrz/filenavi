from enum import Enum
from shutil import rmtree
from pathlib import Path
from os import rename
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy, event
from sqlalchemy.orm import synonym
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, session
from sqlalchemy.exc import NoResultFound

db = SQLAlchemy()


class OrderedEnum(Enum):
    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class Rank(OrderedEnum):
    USER = 1
    ADMIN = 2
    OWNER = 3

    def __str__(self):
        if self == self.USER:
            return "User"
        if self == self.ADMIN:
            return "Admin"
        if self == self.OWNER:
            return "Owner"
        raise ValueError


class LinkConversion(Enum):
    NAME = 1
    ID = 2

    def __str__(self):
        if self == self.ID:
            return "ID"
        if self == self.NAME:
            return "Name"
        raise ValueError


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    _password = db.Column(db.Text, unique=False, nullable=False)
    rank = db.Column(db.Enum(Rank), unique=False, nullable=False)
    link_conversion = db.Column(
        db.Enum(LinkConversion),
        unique=False,
        nullable=False)

    def __init__(self, name: str, password: str, rank: Rank,
                 link_conversion: LinkConversion = LinkConversion.NAME):
        self.name = name
        self.password = password
        self.rank = rank
        self.link_conversion = link_conversion

    def verify(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def home(self, visibility=None, relpath=None) -> Path:
        parent = current_app.config["DATA_DIR"]

        parent /= current_app.config["USERS_DIR"] / str(self.id)

        if visibility is not None:
            parent /= str(visibility)
        elif relpath is not None:
            raise ValueError("Visibility not specified for home directory")

        if relpath is not None:
            parent /= relpath

        return parent.resolve()

    def has_access_to(self, thing):
        if isinstance(thing, User):
            return self == thing or (
                self.rank >= Rank.ADMIN and self.rank > thing.rank)
        if isinstance(thing, File):
            return thing.is_accessible_by(self)
        raise TypeError("Argument must be of type User or File")

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = generate_password_hash(value)

    password = synonym("_password", descriptor=password)

    @staticmethod
    def current():
        if "user_id" in session:
            try:
                user = User.query.filter_by(id=session["user_id"]).one()
            except NoResultFound:
                return None
            return user


@event.listens_for(User, "after_insert")
def create_user_dir(mapper, connect, target):
    for visibility in Visibility:
        target.home(visibility).mkdir(parents=True, exist_ok=True)


@event.listens_for(User, "before_delete")
def delete_user_dir(mapper, connect, target):
    rmtree(target.home())


class Visibility(Enum):
    public = 1
    private = 2

    def __str__(self):
        return self.name

    def toggle(self):
        if self == Visibility.public:
            return Visibility.private
        if self == Visibility.private:
            return Visibility.public


class Share(db.Model):
    __tablename__ = "shares"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    # the owner can delete the share (or transfer ownership)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, name: str):
        self.name = name


class Permission(Enum):
    ADD = 1 # view, upload
    MODIFY = 2 # view, upload, move
    FULL = 3 # view, upload, move, remove


class Membership(db.Model):
    __tablename__ = "memberships"

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)
    share_id = db.Column(db.Integer, db.ForeignKey("share.id"), primary_key=True)
    permission = db.Column(db.Enum(Permission), nullable=False)

    user = relationship('User', backref=backref('user_association'))
    share = relationship('Share', backref=backref('share_association'))


class File:
    def __init__(
            self,
            path: Path,
            owner: User,
            visibility: Visibility = Visibility.private):
        self.path = owner.home(visibility, path)
        self.visibility = visibility
        self.owner = owner

        if self.path.exists():
            stat = self.path.stat()
            self.attributes = {
                "modification": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc),
                "symlink": self.path.is_symlink(),
                "size": stat.st_size}

    def move(self, new_path: Path, force: bool = False):
        parent = self.owner.home(self.visibility)
        if not new_path.is_relative_to(parent):
            raise ValueError("File must be within user directory")

        new_path.parents[0].mkdir(parents=True, exist_ok=True)

        if new_path.exists():
            if new_path.is_dir():
                self.path = self.path.rename(new_path / self.path.name)
            else:
                if not force:
                    raise ValueError("File already exists")
                else:
                    self.path = self.path.replace(new_path)
        else:
            self.path = self.path.rename(new_path)

    def mkdir(self):
        home = self.owner.home(self.visibility)

        if not self.path.is_relative_to(home):
            raise ValueError("File must be within user directory")

        self.path.mkdir(parents=True, exist_ok=True)

    def remove(self, recursive: bool = False):
        home = self.owner.home(self.visibility)

        if not self.path.is_relative_to(home):
            raise ValueError("File must be within user directory")

        if not self.path.exists():
            raise ValueError("File does not exist")

        try:
            self.path.unlink()
        except IsADirectoryError:
            try:
                self.path.rmdir()
            except OSError:
                if not recursive:
                    raise
                else:
                    rmtree(self.path)

    def toggle(self, path: Path, force: bool = False):
        new_visibility = self.visibility.toggle()
        new_path = self.owner.home(new_visibility, relpath=path)

        if not new_path.is_relative_to(self.owner.home(new_visibility)):
            raise ValueError("Path is not relative to home")

        new_path.parents[0].mkdir(parents=True, exist_ok=True)

        if new_path.exists():
            if new_path.is_dir():
                self.path = self.path.rename(new_path / self.path.name)
            else:
                if not force:
                    raise ValueError("File already exists")
                else:
                    self.path = self.path.replace(new_path)
        else:
            self.path = self.path.rename(new_path)

        self.visibility = new_visibility

    def is_accessible_by(self, user) -> bool:
        public = self.visibility == Visibility.public and not self.path.is_dir()

        if user is None:
            return public

        return public or user == self.owner or (
            user.rank >= Rank.ADMIN and user.rank > self.owner.rank)

    @staticmethod
    def format_size(num: int, suffix: str = "B"):
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024
        return f"{num:.1f}Yi{suffix}"
