import os
import io
from pathlib import Path
import dataclasses as dc

import nbformat
from IPython.utils import tz

from nbx_deux.models import BaseModel


@dc.dataclass
class NotebookBundleModel(BaseModel):
    bundle_files: dict
    is_bundle: bool = True


class Bundle(object):
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
    def __init__(self, bundle_path):
        bundle_path = Path(bundle_path)
        self.name = bundle_path.name
        self.bundle_path = bundle_path

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
                if p.suffix != '.pyc'
            ]
        except StopIteration:
            files = []
        return files


class NotebookBundle(Bundle):
    """
    Bundle that represents a Jupyter Notebook.
    """
    @property
    def notebook_content(self):
        filepath = os.path.join(self.bundle_path, self.name)
        with io.open(filepath, 'r', encoding='utf-8') as f:
            try:
                nb = nbformat.read(f, as_version=4)
            except Exception:
                nb = None
            return nb

    @property
    def files(self):
        """
        Return extra files.
        """
        files = super(NotebookBundle, self).files
        assert self.name in files
        files.remove(self.name)
        assert self.name not in files
        return files

    def files_pack(self, file_content=True):
        files = {}
        for fn in self.files:
            with open(os.path.join(self.bundle_path, fn), 'rb') as f:
                data = None
                if file_content:
                    try:
                        data = f.read().decode('utf-8')
                    except UnicodeDecodeError:
                        # TODO how to deal with binary data?
                        # right now we skip
                        continue
                files[fn] = data

        return files

    def get_model(self, root_dir, content=True, file_content=True):
        os_path = os.path.join(self.bundle_path, self.name)
        info = os.stat(os_path)
        last_modified = tz.utcfromtimestamp(info.st_mtime)
        created = tz.utcfromtimestamp(info.st_ctime)

        notebook_content = None
        if content:
            notebook_content = self.notebook_content

        files = self.files_pack(file_content)
        path = os.path.relpath(self.bundle_path, root_dir)
        model = NotebookBundleModel(
            name=self.name,
            path=path,
            last_modified=last_modified,
            created=created,
            type='notebook',
            bundle_files=files,
            content=notebook_content,
        )
        return model


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

        nb_bundle = NotebookBundle(nb_dir)
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
