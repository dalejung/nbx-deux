import dataclasses as dc
import os
from pathlib import Path


from jupyter_server.services.contents.filemanager import FileContentsManager
from jupyter_server.services.contents.manager import ContentsManager
from nbx_deux.nbx_manager import NBXContentsManager, ApiPath
from nbx_deux.root_manager import RootContentsManager


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
    def __init__(self, *args, managers=None, **kwargs):
        super().__init__(*args, **kwargs)
        if managers is None:
            managers = {}
        self.managers = managers
        self.root = RootContentsManager(meta_manager=self)

        # TODO: The below are just testing.
        self.managers['default'] = FileContentsManager(root_dir=self.root_dir)
        self.managers['home'] = FileContentsManager(
            root_dir=str(Path("~").expanduser())
        )

    def get_nbm_from_path(self, path) -> tuple[ContentsManager, ManagerMeta]:
        path = path.strip('/')

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

        nbm = self.managers.get(nbm_path, None)
        if nbm is None:
            raise Exception(f"Could not find {nbm_path=} {path=}")
        return nbm, meta

    # ContentManager API
    def get(self, path: ApiPath, content=True, type=None, format=None):
        nbm, meta = self.get_nbm_from_path(path)
        model = nbm.get(meta.path, content=content, type=type, format=format)

        # meh. if we're changing back to dict so quickly, maybe just use
        # TypedDict instead?
        if hasattr(model, 'asdict'):
            model = model.asdict()

        self.reanchor_paths_with_nbm_path(model, meta)

        return model

    def reanchor_paths_with_nbm_path(self, model, meta):
        # while the local manager doesn't know its nbm_path,
        # we have to add it back in for the metamanager.
        if model['type'] == 'directory':
            if not (content := model.get("content", [])):
                return

            for m in content:
                m['path'] = os.path.join(meta.nbm_path, m['path'])

        # so the path needs to be the full request path.
        if model['type'] == 'notebook':
            model['path'] = os.path.join(meta.nbm_path, model['path'])

    def save(self, model, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.save(model, meta.path)

    def delete_file(self, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.delete_file(meta.path)

    def rename_file(self, old_path: ApiPath, new_path: ApiPath):
        nbm, meta = self.get_nbm_from_path(old_path)
        _new_nbm, new_meta = self.get_nbm_from_path(new_path)
        if nbm is not _new_nbm:
            raise Exception("Cannot rename across child content managers")
        return nbm.rename_file(meta.path, new_meta.path)

    def file_exists(self, path: ApiPath) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.file_exists(meta.path)

    def dir_exists(self, path: ApiPath) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.dir_exists(meta.path)

    def is_hidden(self, path: ApiPath) -> bool:
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.is_hidden(meta.path)

    # Checkpoints api
    def create_checkpoint(self, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.create_checkpoint(meta.path)

    def list_checkpoints(self, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.list_checkpoints(meta.path)

    def restore_checkpoint(self, checkpoint_id, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.restore_checkpoint(checkpoint_id, meta.path)

    def delete_checkpoint(self, checkpoint_id, path: ApiPath):
        nbm, meta = self.get_nbm_from_path(path)
        return nbm.delete_checkpoint(checkpoint_id, meta.path)
