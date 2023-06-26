from nbx_deux.testing import TempDir
from nbformat.v4 import new_notebook, writes


from ..bundle import (
    NotebookBundlePath,
)


def test_notebook_bundle_file():
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

        content = nb_bundle.get_bundle_file_content()
        assert content == nb

        model = nb_bundle.get_model(td)
        assert model.is_bundle is True
        assert model.content == nb
        assert model.bundle_files['howdy.txt'] == 'howdy'
        assert model.name == 'example.ipynb'
        assert model.path == 'subdir/example.ipynb'

        nb_bundle.rename("new_name.ipynb")
        new_model = nb_bundle.get_model(td)

        assert subdir.joinpath('new_name.ipynb').exists()
        assert subdir.joinpath('new_name.ipynb/new_name.ipynb').exists()

        assert new_model.name == 'new_name.ipynb'
        assert new_model.path == 'subdir/new_name.ipynb'
        assert new_model.bundle_files['howdy.txt'] == 'howdy'

        new_model = nb_bundle.get_model(td, file_content=False)
        assert new_model.bundle_files['howdy.txt'] is None
