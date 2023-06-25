from datetime import datetime

from jupyter_server.services.contents.manager import (
    ContentsManager,
)

from nbx_deux.models import BaseModel


class NBXContentsManager(ContentsManager):
    def _base_model(self, path=''):
        """Build the common base of a contents model"""
        # Create the base model.
        now = datetime.now()
        model = BaseModel(
            name=path.rsplit('/', 1)[-1],
            path=path,
            last_modified=now,
            created=now,
        )
        return model
