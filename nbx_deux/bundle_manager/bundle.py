"""
A bundle is a directory that acts like a file.
The directory will contain the actual file with the same name as
bundle_path.name and any other additional files.

bundle_path is only path external logic should see.

/root/frank.txt
/root/frank.txt/frank.txt
/root/frank.txt/metadata.json

In the above setup `/root/frank.txt` is the bundle_path.
`/root/frank/frank.txt` is the actual file.
"""
import os
from pathlib import Path
import dataclasses as dc
from typing import ClassVar, Literal, cast

import nbformat
from IPython.utils import tz

from nbx_deux.models import BaseModel, NotebookModel
from nbx_deux.fileio import (
    _read_notebook,
    _save_notebook,
    check_and_sign,
    ospath_is_writable,
)
from nbx_deux.normalized_notebook import NormalizedNotebookPy


@dc.dataclass(frozen=True, kw_only=True)
class PathItem:
    path: Path
    type: Literal['file', 'directory']
    is_bundle: bool = False

    @property
    def is_regular_file(self):
        return self.type == 'file' and not self.is_bundle


def bundle_get_path_item(os_path):
    os_path = Path(os_path)
    type = 'file'
    is_bundle = False

    if os_path.is_dir():
        if BundlePath.valid_path(os_path):
            type = 'file'
            is_bundle = True
        else:
            type = 'directory'
    item = PathItem(path=os_path, type=type, is_bundle=is_bundle)
    return item


def bundle_list_dir(os_path):
    os_path = Path(os_path)
    content = []
    for p in os_path.iterdir():
        item = bundle_get_path_item(p)
        content.append(item)
    return content


@dc.dataclass(kw_only=True)
class BundleModel(BaseModel):
    type: str = dc.field(default='file', init=False)
    bundle_files: dict
    is_bundle: bool = True


@dc.dataclass(kw_only=True)
class NotebookBundleModel(BundleModel):
    content: nbformat.NotebookNode
    type: str = dc.field(default='notebook', init=False)
    default_format: ClassVar = 'json'

    def __repr__(self):
        content = self.content
        cell_count = len(content['cells'])
        metadata = content['metadata']
        notebook_node_repr = f"NotebookNode({cell_count=}, {metadata=})"
        return (
            f"NotebookBundleModel(name={self.name}, path={self.path}"
            f", content={notebook_node_repr})"
        )


class BundlePath:
    bundle_model_class: ClassVar[type] = BundleModel

    def __init__(self, bundle_path):
        bundle_path = Path(bundle_path)
        self.name = bundle_path.name
        self.bundle_path = bundle_path

    @property
    def bundle_file(self):
        bundle_path = self.bundle_path
        return bundle_path.joinpath(bundle_path.name)

    def __repr__(self):
        cname = self.__class__.__name__
        bundle_path = self.bundle_path
        return f"{cname}({bundle_path=})"

    @property
    def files(self):
        """
        files keys will be name relative to bundle_path

        NOTE: This is not recursive depth.
        """
        try:
            files = [
                str(p.relative_to(self.bundle_path))
                for p in self.bundle_path.iterdir()
                if p.suffix != '.pyc' and p.is_file()
            ]
        except StopIteration:
            files = []
        return files

    def read_bundle_file(self, name):
        filepath = os.path.join(self.bundle_path, name)
        data = None
        with open(filepath, 'rb') as f:
            try:
                data = f.read().decode('utf-8')
            except UnicodeDecodeError:
                pass
                # TODO how to deal with binary data?
                # right now we skip
        return data

    def files_pack(self, file_content=True):
        files = {}
        for fn in self.files:
            # We only want extra files
            if fn == self.name:
                continue

            data = None
            if file_content:
                data = self.read_bundle_file(fn)
            files[fn] = data

        return files

    @staticmethod
    def is_bundle(os_path):
        if not os.path.isdir(os_path):
            return False

        name = os.path.basename(os_path)
        bundle_file = os.path.join(os_path, name)
        return os.path.isfile(bundle_file)

    @classmethod
    def valid_path(cls, os_path):
        return cls.is_bundle(os_path)

    @classmethod
    def iter_bundle_paths(cls, os_path):
        os_path = Path(os_path)
        for p in os_path.iterdir():
            if not p.is_dir():
                continue
            if not cls.valid_path(p):
                continue
            yield p

    @classmethod
    def iter_bundles(cls, os_path):
        for bundle_path in cls.iter_bundle_paths(os_path):
            bundle = cls(bundle_path)
            yield bundle

    def save(self, model):
        bundle_path = self.bundle_path
        if not os.path.exists(bundle_path):
            os.mkdir(bundle_path)

        self.save_bundle_file(model)
        return model

    def save_bundle_file(self, model):
        content = model['content']
        with open(self.bundle_file, 'w') as f:
            f.write(content)

    def get_bundle_file_content(self):
        with open(self.bundle_file, 'r') as f:
            return f.read()

    def write_files(self, model):
        # write files
        bundle_path = self.bundle_path

        files = model['bundle_files']
        for fn, fcontent in files.items():
            filepath = os.path.join(bundle_path, fn)
            with open(filepath, 'w') as f:
                f.write(fcontent)

    def get_model(self, root_dir=None, content=True, file_content=None):
        # default getting file_content to content
        if file_content is None:
            file_content = content

        if root_dir is None:
            root_dir = self.bundle_path

        os_path = self.bundle_file

        bundle_file_content = None
        if content:
            bundle_file_content = self.get_bundle_file_content()

        model = BaseModel.from_filepath_dict(os_path, root_dir)
        # This gets the deets for the actual bundle_file
        # However we dont want the path to point to the actual bundle_file
        path = os.path.relpath(self.bundle_path, root_dir)
        model['path'] = path
        assert model['name'] == self.name

        files = self.files_pack(file_content)
        model = self.bundle_model_class(
            bundle_files=files,
            content=bundle_file_content,
            **model,
        )
        return model

    def rename(self, new_name):
        # first move the notebook file
        new_bundle_path = self.bundle_path.parent.joinpath(new_name)

        if new_bundle_path.exists():
            raise Exception(
                f"Trying to rename to an existing path {new_bundle_path}"
            )

        # note we are renaming file within the old bundle_path. we change the
        # bundle_path next
        new_bundle_file_path = self.bundle_path.joinpath(new_name)
        try:
            os.rename(self.bundle_file, new_bundle_file_path)
        except Exception as e:
            raise Exception((
                "Unknown error renaming notebook: "
                f"{self.name} {new_name} {e}"
            ))

        # finally move the bundle folder
        try:
            os.rename(self.bundle_path, new_bundle_path)
        except Exception as e:
            raise Exception((
                "Unknown error renaming notebook: "
                f"{self.bundle_path} {new_bundle_path} {e}"
            ))

        self.__init__(new_bundle_path)


class NotebookBundlePath(BundlePath):
    """
    Bundle that represents a Jupyter Notebook.
    """
    bundle_model_class = NotebookBundleModel

    @classmethod
    def valid_path(cls, os_path):
        # basically a bundle with ipynb
        name = os.path.basename(os_path)
        if not name.endswith('.ipynb'):
            return False
        return cls.is_bundle(os_path)

    def normalized_dir(self, nb: nbformat.NotebookNode):
        normalized_dir = self.bundle_path.joinpath('_normalized')
        return normalized_dir

    def save_normalized(self, nb: nbformat.NotebookNode):
        normalized_dir = self.normalized_dir(nb)
        normalized_dir.mkdir(exist_ok=True, parents=True)

        nnpy = NormalizedNotebookPy(nb)
        content = nnpy.to_pyfile()
        basename, ext = os.path.splitext(self.bundle_file.name)
        new_filename = basename + '.py'
        new_filepath = normalized_dir.joinpath(new_filename)
        with open(new_filepath, 'w') as f:
            f.write(content)

    def save_bundle_file(self, model: NotebookModel):
        nb = cast(nbformat.NotebookNode, nbformat.from_dict(model['content']))
        check_and_sign(nb)
        _save_notebook(self.bundle_file, nb)
        # WIP
        self.save_normalized(nb)

    def get_bundle_file_content(self):
        nb = _read_notebook(self.bundle_file)
        return nb


if __name__ == '__main__':
    from nbx_deux.testing import TempDir
    from nbformat.v4 import new_notebook, writes

    with TempDir() as td:
        nb_dir = td.joinpath('example.ipynb')
        nb = new_notebook()
        bundle = NotebookBundlePath(nb_dir)
        model = NotebookModel.from_nbnode(nb, name='hi.ipynb', path='hi.ipynb')
        bundle.save(model)
        assert nb_dir.is_dir()

        new_model = bundle.get_model(td)
        assert new_model['content'] == nb
        assert bundle.bundle_path.joinpath('_normalized/example.py').exists()
