from jupyter_server.services.contents.manager import (
    ContentsManager,
)

from jupyter_server.services.contents.checkpoints import (
    Checkpoints
)
from typing import Protocol, runtime_checkable
from traitlets import (
    Instance,
)


class NBXContentsManager(ContentsManager):
    ...
