from nbx_deux.models import DirectoryModel
from nbx_deux.nbx_manager import NBXContentsManager, ApiPath


class RootContentsManager(NBXContentsManager):
    """
    Handle the root path "/"

    Basically creates the psuedo home directory listing
    """
    def __init__(self, *args, meta_manager, **kwargs):
        self.meta_manager = meta_manager
        super().__init__(*args, **kwargs)

    @property
    def managers(self):
        return self.meta_manager.managers

    def _list_nbm_dirs(self):
        dirs = []
        for name in self.managers:
            model = self._get_dir_content_model(name)
            dirs.append(model)
        return dirs

    def get(self, path: ApiPath, content=True, type=None, format=None):
        return self.get_dir(path)

    def _get_dir_content_model(self, name):
        model = {}
        model['name'] = name
        model['path'] = name
        model['type'] = 'directory'
        model['format'] = 'json'
        return model

    def file_exists(self, path: ApiPath):
        return False

    def dir_exists(self, path: ApiPath):
        return True

    def get_dir(self, path: ApiPath, content=True, **kwargs):
        """ retrofit to use old list_dirs. No notebooks """
        dirs = self._list_nbm_dirs()
        model = DirectoryModel.transient(
            path,
            content=dirs,
        )
        return model

    def is_hidden(self, path: ApiPath):
        return False
