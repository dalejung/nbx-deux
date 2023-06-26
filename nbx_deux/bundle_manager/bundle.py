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
import io
from pathlib import Path
import dataclasses as dc
from typing import cast

import nbformat
from IPython.utils import tz

from nbx_deux.models import BaseModel


@dc.dataclass(kw_only=True)
class BundleModel(BaseModel):
    bundle_files: dict
    is_bundle: bool = True


@dc.dataclass(kw_only=True)
class NotebookBundleModel(BundleModel):
    type: str = dc.field(default='notebook', init=False)


class BundlePath:
    bundle_model_class = BundleModel

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

    def get_model(self, root_dir, content=True, file_content=None):
        # default getting file_content to content
        if file_content is None:
            file_content = content

        os_path = self.bundle_file
        info = os.stat(os_path)
        last_modified = tz.utcfromtimestamp(info.st_mtime)
        created = tz.utcfromtimestamp(info.st_ctime)

        bundle_file_content = None
        if content:
            bundle_file_content = self.get_bundle_file_content()

        files = self.files_pack(file_content)
        path = os.path.relpath(self.bundle_path, root_dir)
        model = self.bundle_model_class(
            name=self.name,
            path=path,
            last_modified=last_modified,
            created=created,
            bundle_files=files,
            content=bundle_file_content,
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

    @property
    def notebook_content(self):
        filepath = os.path.join(self.bundle_path, self.name)
        with io.open(filepath, 'r', encoding='utf-8') as f:
            try:
                nb = nbformat.read(f, as_version=4)
            except Exception:
                nb = None
            return nb

    @classmethod
    def valid_path(cls, os_path):
        # basically a bundle with ipynb
        name = os.path.basename(os_path)
        if not name.endswith('.ipynb'):
            return False
        return cls.is_bundle(os_path)

    def save_bundle_file(self, model):
        nb = cast(nbformat.NotebookNode, nbformat.from_dict(model['content']))

        if 'name' in nb.metadata:
            nb.metadata['name'] = u''
        try:
            with io.open(self.bundle_file, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f, version=nbformat.NO_CONVERT)
        except Exception as e:
            raise Exception((
                'Unexpected error while autosaving notebook: '
                f'{self.bundle_file} {e}'
            ))

    def get_bundle_file_content(self):
        with io.open(self.bundle_file, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        return nb


if __name__ == '__main__':
    from nbx_deux.testing import TempDir
    from nbformat.v4 import new_notebook, writes

    with TempDir() as td:
        subdir = td.joinpath('subdir')
        nb_dir = subdir.joinpath('example.ipynb')
        nb_dir.mkdir(parents=True)
        file1 = nb_dir.joinpath('howdy.txt')
        with file1.open('w') as f:
            f.write('howdy')

        nb_file = nb_dir.joinpath('example.ipynb')
        nb = new_notebook()
        nb['metadata']['howdy'] = 'hi'
        with nb_file.open('w') as f:
            f.write(writes(nb))

        nb_bundle = NotebookBundlePath(nb_dir)
        files = nb_bundle.files
        assert 'howdy.txt' in files

        content = nb_bundle.notebook_content
        assert content == nb

        model = nb_bundle.get_model(td)
        assert model.is_bundle is True
        assert model.content == nb
        assert model.bundle_files['howdy.txt'] == 'howdy'
        assert model.name == 'example.ipynb'
        assert model.path == 'subdir/example.ipynb'
