"""
Paths:
    os_path: full absolute file path
    path: relative path to root_dir (url path)
"""
import os
import dataclasses as dc
from datetime import datetime
from typing import Any

from jupyter_server import _tz as tz
from jupyter_server.services.contents.filemanager import FileContentsManager

RelPath = str


def fcm_base_model(os_path, root_dir=None):
    """
    Use the FileContentsManager to derive a base model.

    Unsure if this will be only for testing.
    """
    if root_dir is None:
        root_dir, path = os.path.split(os_path)
    else:
        path = os.path.relpath(os_path, root_dir)

    fcm = FileContentsManager(root_dir=str(root_dir))
    model = fcm._base_model(path)
    return model


def ospath_is_writable(os_path):
    try:
        return os.access(os_path, os.W_OK)
    except OSError:
        return False


def get_ospath_metadata(os_path):
    info = os.lstat(os_path)

    size = None
    try:
        # size of file
        size = info.st_size
    except (ValueError, OSError):
        pass

    try:
        last_modified = tz.utcfromtimestamp(info.st_mtime)
    except (ValueError, OSError):
        # Files can rarely have an invalid timestamp
        # https://github.com/jupyter/notebook/issues/2539
        # https://github.com/jupyter/notebook/issues/2757
        # Use the Unix epoch as a fallback so we don't crash.
        last_modified = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

    try:
        created = tz.utcfromtimestamp(info.st_ctime)
    except (ValueError, OSError):  # See above
        created = datetime(1970, 1, 1, 0, 0, tzinfo=tz.UTC)

    return {'size': size, 'last_modified': last_modified, 'created': created}


@dc.dataclass(kw_only=True)
class BaseModel:
    """
    Derived from `FileContentsManager._base_model`
    """
    name: str
    path: str  # Path is relative to root.
    last_modified: datetime
    created: datetime
    type: str | None = None
    content: Any | None = None
    format: str | None = None
    mimetype: str | None = None
    size: int | None = None
    writable: bool | None = None

    @classmethod
    def transient(cls, path, **kwargs):
        """
        Helper function for models that aren't "real" like if displaying
        weather info in filelistings.
        """
        now = datetime.now()

        created = kwargs.pop('created', now)
        last_modified = kwargs.pop('last_modified', now)

        return cls(
            name=path.rsplit('/', 1)[-1],
            path=path,
            created=created,
            last_modified=last_modified,
            **kwargs,
        )

    @classmethod
    def from_filepath(cls, os_path, root_dir=None):
        f_metadata = get_ospath_metadata(os_path)

        if root_dir is None:
            root_dir, path = os.path.split(os_path)
        else:
            path = os.path.relpath(os_path, root_dir)
        name = os.path.split(path)[1]
        writable = ospath_is_writable(os_path)
        model = cls(
            name=name,
            path=path,
            **f_metadata,
            writable=writable,
        )
        return model

    def asdict(self):
        return dc.asdict(self)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    def __iter__(self):
        return iter(self.asdict())

    def items(self):
        return self.asdict().items()

    def keys(self):
        return self.asdict().keys()


@dc.dataclass(kw_only=True)
class DirectoryModel(BaseModel):
    type: str = dc.field(default='directory', init=False)
    format: str = dc.field(default='json', init=False)


if __name__ == '__main__':
    from pathlib import Path
    filepath = Path(__file__)
    fcm_model = fcm_base_model(filepath, root_dir=filepath.parents[2])
    model = BaseModel.from_filepath(filepath, root_dir=filepath.parents[2])
