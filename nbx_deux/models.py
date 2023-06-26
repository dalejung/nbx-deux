"""
Paths:
    os_path: full absolute file path
    path: relative path to root_dir (url path)
"""
import copy
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
from jupyter_server.utils import ApiPath, to_os_path

from nbx_deux.fileio import (
    FCM_HIDE_GLOBS,
    get_ospath_metadata,
    mark_trusted_cells,
    ospath_is_writable,
    _read_file,
    _read_notebook,
    should_list,
    validate_notebook_model,
)

RelPath = str


def model_to_dict(obj) -> dict:
    """
    Modified dc.asdict that allows Models to control how they turn into dicts.
    """
    if not isinstance(obj, BaseModel):
        raise Exception(f"model_to_dict only works on BaseModel {type(obj)}")
    dct = _model_to_dict(obj)
    dct = cast(dict, dct)
    return dct


def _model_to_dict(obj):
    if isinstance(obj, BaseModel):
        results = {}
        for k, v in obj.asdict(shallow=True).items():
            results[k] = _model_to_dict(v)
        return results
    elif dc._is_dataclass_instance(obj):
        result = []
        for f in dc.fields(obj):
            value = _model_to_dict(getattr(obj, f.name))
            result.append((f.name, value))
        return dict(result)
    elif isinstance(obj, tuple) and hasattr(obj, '_fields'):
        return type(obj)(*[_model_to_dict(v) for v in obj])
    elif isinstance(obj, (list, tuple)):
        # Assume we can create an object of this type by passing in a
        # generator (which is not true for namedtuples, handled
        # above).
        return type(obj)(_model_to_dict(v) for v in obj)
    elif isinstance(obj, dict):
        return type(obj)((_model_to_dict(k),
                          _model_to_dict(v))
                         for k, v in obj.items())
    else:
        return copy.deepcopy(obj)


def default_model_get(path: ApiPath, content, root_dir):
    """
    Normally for directory type listings the ContentsManager.get is called for each subitem.
    The logic for determining the models can be different per CM. The Models here are meant to be
    divorced from CM logic directly so we have this default simple model generator to mimic
    FileContentsManager.get
    """
    os_path = to_os_path(path, root_dir)
    if os.path.isfile(os_path) and os_path.endswith('.ipynb'):
        model = NotebookModel.from_filepath(os_path, content=content)
    elif os.path.isdir(os_path):
        model = DirectoryModel.from_filepath(
            os_path,
            root_dir=root_dir,
            content=content
        )
    else:
        model = FileModel.from_filepath(
            os_path,
            root_dir=root_dir,
            content=content,
        )
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
    message: str | None = None

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
    def from_filepath_dict(cls, os_path, root_dir=None) -> dict:
        f_metadata = get_ospath_metadata(os_path)

        if root_dir is None:
            # default to root dir being the parent.
            root_dir, path = os.path.split(os_path)
        else:
            path = os.path.relpath(os_path, root_dir)
            if path == '.':
                path = ''

        name = os.path.split(path)[1]
        writable = ospath_is_writable(os_path)

        model = dict(
            name=name,
            path=path,
            **f_metadata,
            writable=writable,
        )
        return model

    @classmethod
    def from_filepath(cls, os_path, root_dir=None, **kwargs):
        model_dict = cls.from_filepath_dict(
            os_path,
            root_dir=root_dir,
            **kwargs
        )
        return cls(**model_dict)

    def asdict(self, shallow=False) -> dict:
        if shallow is False:
            return model_to_dict(self)

        dct = self._shallow_asdict()
        if 'message' in dct and dct['message'] is None:
            dct.pop('message')
        return dct

    def _shallow_asdict(self):
        result = {}
        for f in dc.fields(self):
            value = getattr(self, f.name)
            result[f.name] = value
        return result

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
    def from_filepath_dict(cls, os_path, root_dir=None, content=True, format=None):
        if not os.path.isfile(os_path):
            raise Exception(f"FileModel called on non-file path {os_path=}")

        model = BaseModel.from_filepath_dict(os_path, root_dir=root_dir)
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

        return model


@dc.dataclass(kw_only=True)
class NotebookModel(BaseModel):
    type: str = dc.field(default='notebook', init=False)

    @classmethod
    def from_filepath_dict(cls, os_path, root_dir=None, content=True, format=None):
        model = BaseModel.from_filepath_dict(os_path, root_dir=root_dir)

        if content:
            validation_error: dict = {}
            nb = _read_notebook(os_path)
            mark_trusted_cells(nb)
            model["content"] = nb
            # Copying jupyter idiom of only setting format when content is requested
            model["format"] = "json"
            validate_notebook_model(model, validation_error)

        return model


@dc.dataclass(kw_only=True)
class DirectoryModel(BaseModel):
    type: str = dc.field(default='directory', init=False)

    def contents_dict(self):
        if not self.content:
            return {}

        dct = {}
        for row in self.content:
            dct[row['path']] = row
        return dct

    @classmethod
    def get_dir_content(
        cls,
        os_dir,
        path,
        *,
        model_get,
        allow_hidden=False,
        hide_globs=FCM_HIDE_GLOBS
    ):
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
    def from_filepath_dict(
        cls,
        os_path,
        root_dir=None,
        content=True,
        model_get=None
    ):

        # Default Directory root_dir to os_path
        if root_dir is None:
            root_dir = os_path

        model = BaseModel.from_filepath_dict(
            os_path,
            root_dir=root_dir,
        )
        model["size"] = None

        if content:
            # model_get is ContentsManager.get or default_model_get which mimics
            # the CM logic without needing a CM. This will be wrong for things
            # like Bundles which *require* the specifc bundle logic to correctly
            # return notebooks/files/dirs.
            if model_get is None:
                model_get = partial(default_model_get, root_dir=root_dir)
            content = cls.get_dir_content(
                os_path,
                model['path'],
                model_get=model_get
            )
            model['content'] = content
            # Copying jupyter idiom of only setting format when content is requested
            model["format"] = "json"

        return model


if __name__ == '__main__':
    from nbx_deux.testing import TempDir
    from nbformat import v4
    with TempDir() as td:
        nb_file = td.joinpath('example.ipynb')
        nb = v4.new_notebook()
        nb['metadata']['howdy'] = 'hi'
        with nb_file.open('w') as f:
            f.write(v4.writes(nb))

        fcm = FileContentsManager(root_dir=str(td))
        fcm_model = fcm.get("example.ipynb")

        model = NotebookModel.from_filepath(nb_file, root_dir=td)
        assert model.asdict() == fcm_model
