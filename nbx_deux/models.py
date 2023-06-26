"""
Paths:
    os_path: full absolute file path
    path: relative path to root_dir (url path)
"""
import errno
import os
import dataclasses as dc
from datetime import datetime
import mimetypes
from typing import Any, cast
import stat
from functools import partial
from jupyter_core.paths import is_file_hidden
from jupyter_server.services.contents.filemanager import FileContentsManager

from nbx_deux.fileio import (
    get_ospath_metadata,
    ospath_is_writable,
    _read_file,
    _read_notebook,
    should_list,
)

RelPath = str


def default_model_get(path, content, root_dir):
    os_path = os.path.join(root_dir, path)
    if os.path.isfile(os_path) and os_path.endswith('.ipynb'):
        model = NotebookModel.from_filepath(os_path, content=content)
    elif os.path.isdir(os_path):
        model = DirectoryModel.from_filepath(
            os_path,
            root_dir=root_dir,
            content=content
        )
    else:
        model = BaseModel.from_filepath(
            os_path,
            root_dir=root_dir
        )
    return model


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
    def from_filepath(cls, os_path, root_dir=None, asdict=False):
        f_metadata = get_ospath_metadata(os_path)

        if root_dir is None:
            # default to root dir being the parent.
            root_dir, path = os.path.split(os_path)
        else:
            path = os.path.relpath(os_path, root_dir)
        name = os.path.split(path)[1]
        writable = ospath_is_writable(os_path)

        if asdict:
            cls = dict

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
class FileModel(BaseModel):
    type: str = dc.field(default='file', init=False)

    @classmethod
    def from_filepath(cls, os_path, root_dir=None, content=True, format=None, asdict=False):
        model = BaseModel.from_filepath(os_path, root_dir=root_dir, asdict=True)
        model = cast(dict, model)
        model["mimetype"] = mimetypes.guess_type(os_path)[0]

        if content:
            content, format = _read_file(os_path, format)
            if model["mimetype"] is None:
                default_mime = {
                    "text": "text/plain",
                    "base64": "application/octet-stream",
                }[format]
                model["mimetype"] = default_mime

            model.update(
                content=content,
                format=format,
            )

        if asdict:
            cls = dict

        return cls(**model)


@dc.dataclass(kw_only=True)
class NotebookModel(BaseModel):
    type: str = dc.field(default='notebook', init=False)
    format: str = dc.field(default='json', init=False)

    @classmethod
    def from_filepath(cls, os_path, root_dir=None, content=True, format=None, asdict=False):
        model = BaseModel.from_filepath(os_path, root_dir=root_dir, asdict=True)
        model = cast(dict, model)
        if content:
            validation_error: dict = {}
            nb = _read_notebook(os_path)

            self.mark_trusted_cells(nb, path)
            model["content"] = nb
            self.validate_notebook_model(model, validation_error)


@dc.dataclass(kw_only=True)
class DirectoryModel(BaseModel):
    type: str = dc.field(default='directory', init=False)
    format: str = dc.field(default='json', init=False)

    @classmethod
    def get_dir_content(cls, os_dir, path, *, model_get, allow_hidden=True, hide_globs=[]):
        contents = []
        for name in os.listdir(os_dir):
            try:
                os_path = os.path.join(os_dir, name)
            except UnicodeDecodeError as e:
                continue

            try:
                st = os.lstat(os_path)
            except OSError as e:
                continue

            if (
                not stat.S_ISLNK(st.st_mode)
                and not stat.S_ISREG(st.st_mode)
                and not stat.S_ISDIR(st.st_mode)
            ):
                continue

            try:
                if should_list(name, hide_globs) and (
                    allow_hidden or not is_file_hidden(os_path, stat_res=st)
                ):
                    contents.append(model_get(path=f"{path}/{name}", content=False))
            except OSError as e:
                # ELOOP: recursive symlink, also don't show failure due to permissions
                if e.errno not in [errno.ELOOP, errno.EACCES]:
                    pass
        return contents

    @classmethod
    def from_filepath(cls, os_path, root_dir=None, content=True,
                      asdict=False, model_get=None):
        # Default Directory root_dir to os_path
        if root_dir is None:
            root_dir = os_path

        model = BaseModel.from_filepath(
            os_path,
            root_dir=root_dir,
            asdict=True
        )
        model = cast(dict, model)
        model["size"] = None

        if content:
            if model_get is None:
                model_get = partial(default_model_get, root_dir=root_dir)
            content = cls.get_dir_content(
                os_path,
                model['path'],
                model_get=model_get
            )
            model['content'] = content

        if asdict:
            cls = dict

        return cls(**model)


if __name__ == '__main__':
    from pathlib import Path
    filepath = Path(__file__)
    fcm_model = fcm_base_model(filepath, root_dir=filepath.parents[2])
    model = BaseModel.from_filepath(filepath, root_dir=filepath.parents[2])
