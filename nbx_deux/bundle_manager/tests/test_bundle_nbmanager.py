from nbformat.v4 import new_notebook, writes

from nbx_deux.testing import TempDir
from ..bundle_nbmanager import (
    BundleContentsManager
)


def stage_bundle_workspace(td):
    """ simple file setup for testing bundles """
    subdir = td.joinpath('subdir')

    regular_nb = td.joinpath("regular.ipynb")
    nb = new_notebook()
    with regular_nb.open('w') as f:
        f.write(writes(nb))

    regular_file = td.joinpath("sup.txt")
    with regular_file.open('w') as f:
        f.write("sups")

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

    # try a regular bundle
    bundle_dir = td.joinpath('example.txt')
    bundle_dir.mkdir(parents=True)
    bundle_file = bundle_dir.joinpath('example.txt')
    with bundle_file.open('w') as f:
        f.write("regular ole bundle")


def test_bundle_contents_manager():
    with TempDir() as td:
        stage_bundle_workspace(td)
        nbm = BundleContentsManager(root_dir=str(td))
        # NOTE: sometimes we get a 1.
        model = nbm.get("", content=1)  # type: ignore
        model2 = nbm.get("", content=True)  # type: ignore
        assert model.asdict() == model2.asdict()

        model_dict = model.asdict()
        assert model_dict['format'] == 'json'
        contents_dict = model.contents_dict()

        assert contents_dict['example.txt']['type'] == 'file'
        assert contents_dict['example.txt']['is_bundle'] is True
        assert contents_dict['example.txt']['content'] is None

        bundle_model = nbm.get("example.txt")
        assert bundle_model['type'] == 'file'
        assert bundle_model['is_bundle'] is True
        assert bundle_model['content'] == 'regular ole bundle'

        assert contents_dict['subdir']['type'] == 'directory'
        assert contents_dict['subdir']['content'] is None

        assert contents_dict['regular.ipynb']['type'] == 'notebook'
        assert contents_dict['regular.ipynb']['content'] is None

        assert contents_dict['sup.txt']['type'] == 'file'
        assert contents_dict['sup.txt']['content'] is None

        notebook_model = nbm.get("subdir/example.ipynb")

        assert notebook_model['type'] == 'notebook'
        assert notebook_model['is_bundle'] is True
        assert notebook_model['format'] == 'json'
        assert notebook_model['bundle_files'] == {'howdy.txt': 'howdy'}
        correct = new_notebook()
        correct['metadata']['howdy'] = 'hi'
        assert notebook_model['content'] == correct

        subdir_model = nbm.get("subdir")
        subdir_contents_dict = subdir_model.contents_dict()
        assert subdir_contents_dict['subdir/example.ipynb']['type'] == 'notebook'
        assert subdir_contents_dict['subdir/example.ipynb']['is_bundle'] is True

        nb_model = nbm.get("subdir/example.ipynb", content=False)
        assert subdir_contents_dict['subdir/example.ipynb'] == nb_model


if __name__ == '__main__':
    ...
