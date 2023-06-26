import os.path
from pathlib import Path

from jupyter_server.services.contents.filemanager import FileContentsManager

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
