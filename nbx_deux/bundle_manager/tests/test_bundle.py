from nbx_deux.testing import TempDir
from nbformat.v4 import new_notebook, writes


from ..bundle import (
    NotebookBundle,
)


def test_notebook_bundle():
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
