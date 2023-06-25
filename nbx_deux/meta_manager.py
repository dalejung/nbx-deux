import dataclasses as dc
import os

from traitlets import (
    TraitError,
    Unicode,
    default,
    validate,
)
from jupyter_server.services.contents.filemanager import FileContentsManager
from jupyter_server.services.contents.manager import ContentsManager
from nbx_deux.nbx_manager import NBXContentsManager


@dc.dataclass(kw_only=True)
class ManagerMeta:
    """
    """
    # the original request path
    request_path: str
    # nbm alias
    nbm_path: str
    path: str


class MetaManager(NBXContentsManager):
    root_dir = Unicode(config=True)

    # TODO: move this out?
    @default("root_dir")
    def _default_root_dir(self):
        try:
            return self.parent.root_dir
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

    def __init__(self, *args, managers=None, **kwargs):
        super().__init__(*args, **kwargs)
        if managers is None:
            managers = {}
        self.managers = managers
        self.root = FileContentsManager(root_dir=self.root_dir)

        # default probably should not exist. 
        # mostly here for testing / stubbing things out.
        self.default = FileContentsManager(root_dir=self.root_dir)

    def get_nbm_from_path(self, path) -> tuple[ContentsManager, ManagerMeta]:
        # we are on root
        if not path:
            meta = ManagerMeta(
                request_path=path,
                nbm_path='',
                path='',
            )
            return self.root, meta

        bits = path.split(os.sep)
        nbm_path = bits.pop(0)
        local_path = os.sep.join(bits)
        meta = ManagerMeta(
            request_path=path,
            nbm_path=nbm_path,
            path=local_path,
        )

        nbm = self.managers.get(nbm_path, self.default)

        return nbm, meta

    # ContentManager API
    def get(self, path, content=True, type=None, format=None):
        nbm, meta = self.get_nbm_from_path(path)
        model = nbm.get(meta.path, content=content, type=type, format=format)

        # while the local manager doesn't know its nbm_path,
        # we have to add it back in for the metamanager.
        if model['type'] == 'directory':
            content = model.get("content", [])
            for m in content:
                m['path'] = os.path.join(meta.nbm_path, m['path'])

        # so the path needs to be the full request path.
        if model['type'] == 'notebook':
            model['path'] = os.path.join(meta.nbm_path, model['path'])

        return model

    def save(self, model, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.save(model, meta.path)

    def delete_file(self, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.delete_file(meta.path)

    def rename_file(self, old_path, new_path):
        nbm, meta = self.get_nbm_from_path(old_path)
        _new_nbm, new_meta = self.get_nbm_from_path(old_path)
        if nbm is not _new_nbm:
            raise Exception("Cannot rename across child content managers")
        return nbm.rename_file(meta.path, new_meta.path)

    def file_exists(self, path) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.file_exists(meta.path)

    def dir_exists(self, path) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.dir_exists(meta.path)

    def is_hidden(self, path) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.is_hidden(meta.path)

    # Checkpoints api
    def create_checkpoint(self, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.create_checkpoint(meta.path)

    def list_checkpoints(self, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.list_checkpoints(meta.path)

    def restore_checkpoint(self, checkpoint_id, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.restore_checkpoint(checkpoint_id, meta.path)

    def delete_checkpoint(self, checkpoint_id, path):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.delete_checkpoint(checkpoint_id, meta.path)
