import os
import io
from pathlib import Path

import nbformat
from IPython.utils import tz


class Bundle(object):
    def __init__(self, path):
        path = Path(path)
        self.name = path.name
        self.path = path

    def __repr__(self):
        cname = self.__class__.__name__
        name = self.name
        path = self.path
        return f"{cname}({name=}, {path=})"

    @property
    def files(self):
        try:
            files = [
                str(p.relative_to(self.path))
                for p in self.path.iterdir()
                if p.suffix != '.pyc'
            ]
        except StopIteration:
            files = []
        return files


class NotebookBundle(Bundle):

    @property
    def notebook_content(self):
        filepath = os.path.join(self.path, self.name)
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
            with open(os.path.join(self.path, fn), 'rb') as f:
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

    def get_model(self, content=True, file_content=True):
        os_path = os.path.join(self.path, self.name)
        info = os.stat(os_path)
        last_modified = tz.utcfromtimestamp(info.st_mtime)
        created = tz.utcfromtimestamp(info.st_ctime)

        # Create the notebook model.
        model = {}
        model['name'] = self.name
        model['path'] = self.path
        model['last_modified'] = last_modified
        model['created'] = created
        model['type'] = 'notebook'
        model['is_bundle'] = True
        model['content'] = None

        if content:
            model['content'] = self.notebook_content

        files = self.files_pack(file_content)
        model['__files'] = files
        return model


if __name__ == '__main__':
    from nbx_deux.testing import TempDir
    from nbformat.v4 import new_notebook, writes

    with TempDir() as td:
        nb_dir = td.joinpath('example.ipynb')
        nb_dir.mkdir()
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

        model = nb_bundle.get_model()
        assert model['is_bundle'] is True
        assert model['content'] == nb
        assert model['__files']['howdy.txt'] == 'howdy'
