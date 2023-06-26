import os

from traitlets import (
    TraitError,
    Unicode,
    default,
    validate,
)
from jupyter_server.services.contents.manager import (
    ContentsManager,
)
from jupyter_server.utils import (
    ApiPath as ApiPath,
)

from nbx_deux.models import BaseModel


class NBXContentsManager(ContentsManager):
    root_dir = Unicode(config=True)

    # Even though not all CMs will make use of root_dir, feels cleaner to
    # keep it here.
    @default("root_dir")
    def _default_root_dir(self):
        try:
            return self.parent.root_dir  # type: ignore
        except AttributeError:
            return os.getcwd()

    @validate("root_dir")
    def _validate_root_dir(self, proposal):
        value = proposal["value"]
        if not os.path.isabs(value):
            # If we receive a non-absolute path, make it absolute.
            value = os.path.abspath(value)
        if not os.path.isdir(value):
            raise TraitError("%r is not a directory" % value)
        return value

    def _base_model(self, path: ApiPath):
        """Build the common base of a contents model"""
        # Create the base model.
        model = BaseModel.transient(path)
        return model
