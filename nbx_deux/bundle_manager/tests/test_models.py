from pathlib import Path

from ..models import (
    BaseModel,
    fcm_base_model,
)


def test_base_model():
    filepath = Path(__file__)
    root_dir = filepath.parents[2]
    fcm_model = fcm_base_model(filepath, root_dir=root_dir)
    model = BaseModel.from_filepath(filepath, root_dir=root_dir)
    assert model.name == filepath.name
    assert model.path == str(filepath.relative_to(root_dir))

    model_dict = model.asdict()
    model_dict.pop('type')
    assert model_dict == fcm_model

    # no root_dir
    fcm_model = fcm_base_model(filepath)
    model = BaseModel.from_filepath(filepath)
    assert model.name == filepath.name

    model_dict = model.asdict()
    model_dict.pop('type')
    assert model_dict == fcm_model
