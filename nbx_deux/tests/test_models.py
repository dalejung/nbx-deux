import os.path
from pathlib import Path
import pytest

from nbformat import v4
from jupyter_server.services.contents.filemanager import FileContentsManager

from nbx_deux.testing import TempDir
from ..models import (
    BaseModel,
    FileModel,
    NotebookModel,
    DirectoryModel,
)


def test_base_model():
    filepath = Path(__file__)
    root_dir = filepath.parents[2]
    fcm = FileContentsManager(root_dir=str(root_dir))
    path = os.path.relpath(filepath, root_dir)
    fcm_model = fcm._base_model(path)
    model = BaseModel.from_filepath(filepath, root_dir=root_dir)
    assert model.name == filepath.name
    assert model.path == str(filepath.relative_to(root_dir))

    model_dict = model.asdict()
    model_dict.pop('type')
    assert model_dict == fcm_model

    # no root_dir
    root_dir = filepath.parents[0]
    fcm = FileContentsManager(root_dir=str(root_dir))
    fcm_model = fcm._base_model(filepath.name)
    model = BaseModel.from_filepath(filepath)
    assert model.name == filepath.name

    model_dict = model.asdict()
    model_dict.pop('type')
    assert model_dict == fcm_model


def test_file_model():
    filepath = Path(__file__)
    root_dir = filepath.parents[2]
    fcm = FileContentsManager(root_dir=str(root_dir))
    path = os.path.relpath(filepath, root_dir)

    fcm_model = fcm.get(path)

    model = FileModel.from_filepath(filepath, root_dir=root_dir)
    assert model.asdict() == fcm_model

    fcm_model = fcm.get(path, content=False)
    model = FileModel.from_filepath(filepath, root_dir=root_dir, content=False)
    assert model.asdict() == fcm_model

    with pytest.raises(Exception, match="FileModel called on non-file path"):
        FileModel.from_filepath(root_dir, root_dir=root_dir)


def test_directory_model():
    import jupyter_server
    filepath = Path(jupyter_server.__file__)
    root_dir = filepath.parent
    fcm = FileContentsManager(root_dir=str(root_dir))

    fcm_model = fcm.get("")

    model = DirectoryModel.from_filepath(root_dir, root_dir=root_dir)
    model_dict = model.asdict()
    model_content = model_dict.pop('content')
    fcm_content = fcm_model.pop('content')
    assert len(model_content) > 5
    assert model_dict == fcm_model
    for left, right in zip(model_content, fcm_content):
        assert left == right


def test_notebook_model():
    with TempDir() as td:
        nb_file = td.joinpath('example.ipynb')
        nb = v4.new_notebook()
        nb['metadata']['howdy'] = 'hi'
        with nb_file.open('w') as f:
            f.write(v4.writes(nb))

        fcm = FileContentsManager(root_dir=str(td))
        fcm_model = fcm.get("example.ipynb")

        model = NotebookModel.from_filepath(nb_file, root_dir=td)
        assert model.type == 'notebook'
        assert model.asdict() == fcm_model
