from nbx_deux.nbx_manager import NBXContentsManager


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

    def get(self, path, content=True, type=None, format=None):
        return self.get_dir(path)

    def _get_dir_content_model(self, name):
        model = {}
        model['name'] = name
        model['path'] = name
        model['type'] = 'directory'
        model['format'] = 'json'
        return model

    def file_exists(self, path):
        return False

    def dir_exists(self, path):
        return True

    def get_dir(self, path='', content=True, **kwargs):
        """ retrofit to use old list_dirs. No notebooks """
        model = self._base_model(path)
        model.type = 'directory'
        dirs = self._list_nbm_dirs()
        model.content = dirs
        model.format = 'json'
        return model

    def is_hidden(self, path):
        return False
