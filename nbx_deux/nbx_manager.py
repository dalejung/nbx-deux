from datetime import datetime

from jupyter_server.services.contents.manager import (
    ContentsManager,
)

from nbx_deux.models import BaseModel


class NBXContentsManager(ContentsManager):
    def _base_model(self, path=''):
        """Build the common base of a contents model"""
        # Create the base model.
        model = BaseModel.transient(path)
        return model
