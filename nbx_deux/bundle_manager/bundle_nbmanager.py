import datetime
import os
from pathlib import Path
import shutil
from jupyter_server.services.contents.fileio import FileManagerMixin
from jupyter_server.utils import to_os_path


from traitlets import Unicode
from IPython.utils import tz
from jupyter_server.services.contents.filemanager import FileContentsManager

from nbx_deux.models import DirectoryModel, NotebookModel

from ..nbx_manager import NBXContentsManager, ApiPath
from .bundle import NotebookBundlePath, BundlePath, bundle_get_path_item


class BundleContentsManager(FileManagerMixin, NBXContentsManager):
    trash_dir = Unicode(config=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fm = FileContentsManager(root_dir=self.root_dir)

    def is_bundle(self, path: ApiPath | Path):
        if isinstance(path, Path) and path.is_absolute():
            os_path = path
        else:
            os_path = self._get_os_path(path=path)
        return BundlePath.valid_path(os_path)

    def is_notebook(self, path: ApiPath, type=None):
        return (type is None and path.endswith(".ipynb"))

    def get_bundle(self, path: ApiPath, type=None):
        os_path = self._get_os_path(path=path)
        if type == "notebook" or self.is_notebook(path, type):
            bundle = NotebookBundlePath(os_path)
        else:
            bundle = BundlePath(os_path)
        return bundle

    def get(self, path, content=True, type=None, format=None):
        os_path = self._get_os_path(path=path)
        path_item = bundle_get_path_item(os_path)
        # TODO: Someday we might allow accessing other files in bundle. But that's later.
        # This will also handle any non bundle notebooks
        if path_item.type == 'file':
            if type == "directory":
                raise Exception(f"{path} is not a directory")
            if not path_item.is_bundle:
                # regular files use fm
                return self.fm.get(path, content=content, type=type, format=format)
            else:
                return self.bundle_get(path, content=content, type=type, format=format)

        # non content directories can just use fcm.
        if path_item.type == 'directory':
            if type not in (None, "directory"):
                raise Exception(f"{path} is a directory not a {type}")

            if not content:
                return self.fm.get(path, content=content)
            else:
                return self.get_dir(path, content)

        raise Exception(f"Unable to handle {path}")

    def get_dir(self, path, content=True):
        os_path = self._get_os_path(path=path)
        model = DirectoryModel.from_filepath(
            os_path,
            self.root_dir,
            content=content,
            model_get=self.get,  # use out CM.get logic
        )
        return model

    def bundle_get(self, path, content=True, type=None, format=None):
        bundle = self.get_bundle(path, type=type)
        model = bundle.get_model(self.root_dir, content=content)
        return model

    def save(self, model, path):
        os_path = self._get_os_path(path=path)
        is_notebook = self.is_notebook(path)
        is_new = not os.path.exists(os_path)
        is_new_notebook = is_new and is_notebook
        # new files default to bundle
        if self.is_bundle(path) or is_new_notebook:
            bundle = self.get_bundle(path)
            bundle.save(model)
            # refresh
            model = self.get(path, content=False)
            return model.asdict()

        return self.fm.save(model, path)

    def delete_file(self, path):
        if self.is_bundle(path):
            raise NotImplementedError("Deleting bundle not supported yet")
        return self.fm.delete_file(path)

    def rename_file(self, old_path, new_path):
        if self.is_bundle(old_path):
            bundle = self.get_bundle(old_path)
            new_name = os.path.basename(new_path)
            bundle.rename(new_name)
            return
        return self.fm.rename_file(old_path, new_path)

    def file_exists(self, path):
        os_path = self._get_os_path(path=path)
        if self.is_bundle(path):
            return True
        return os.path.isfile(os_path)

    def dir_exists(self, path: ApiPath):
        # if bundle the dir is a file
        if self.is_bundle(path):
            return False
        os_path = self._get_os_path(path=path)
        return os.path.isdir(os_path)

    def save_file(self, model, path=''):
        """Save the notebook model and return the model with no content."""

        model = self.fm.save(model, path)
        return model

    def is_hidden(self, path):
        return self.fm.is_hidden(path)

    def get_kernel_path(self, path, model=None):
        if not self.is_bundle(path):
            return self.fm.get_kernel_path(path, model)
        return path

    def delete_all_checkpoints(self, path):
        if not self.is_bundle(path):
            return self.fm.checkpoints.delete_all_checkpoints(path)

    def rename_all_checkpoints(self, old_path, new_path):
        if not self.is_bundle(old_path):
            return self.fm.checkpoints.rename_all_checkpoints(old_path, new_path)

    def delete_bundle(self, path):
        if not self.is_bundle(path):
            return self.fm.delete_file(path)

        if not self.trash_dir:
            raise Exception("Removing bundle not implemented. Add trash_dir")
            return

        # get into bundle dir
        bundle = self.get_bundle(path)
        bundle_path = bundle.bundle_path

        trash_name = path.replace(os.path.sep, '__')

        trash_path = os.path.join(self.trash_dir, trash_name)

        i = 0
        while os.path.exists(trash_path):
            bits = trash_name.rsplit('.')
            bits[0] = bits[0] + '-' + str(i)
            trash_name = '.'.join(bits)
            trash_path = os.path.join(self.trash_dir, trash_name)

        shutil.move(bundle_path, trash_path)

    # Checkpoint-related utilities
    def _get_checkpoint_dir(self, path):
        checkpoint_dir = os.path.join(path, '.ipynb_checkpoints')
        return ApiPath(checkpoint_dir)

    def get_checkpoint_path(self, checkpoint_id, path):
        """find the path to a checkpoint"""
        path = path.strip('/')
        checkpoint_dir = self._get_checkpoint_dir(path)
        name = path.rsplit('/', 1)[-1]
        basename, ext = os.path.splitext(name)
        filename = u"{name}---{checkpoint_id}{ext}".format(
            name=basename,
            checkpoint_id=checkpoint_id,
            ext=ext,
        )
        cp_path = os.path.join(checkpoint_dir, filename)
        return ApiPath(cp_path)

    def extract_checkpoint_id(self, path):
        """
        Not currently used...

        extra checkpoint_id from strings of form
        "{basename}---{checkpoint_id}.ipynb"
        """
        name = path.rsplit('/', 1)[-1]
        basename, ext = os.path.splitext(name)
        checkpoint_basename, _ = os.path.splitext(name)
        prefix = "{name}---".format(name=basename)
        return checkpoint_basename.replace(prefix, '')

    def get_checkpoint_model(self, checkpoint_id, path):
        """construct the info dict for a given checkpoint"""
        path = path.strip('/')
        cp_path = self.get_checkpoint_path(checkpoint_id, path)
        os_cp_path = self._get_os_path(path=cp_path)
        stats = os.stat(os_cp_path)
        last_modified = tz.utcfromtimestamp(stats.st_mtime)
        info = dict(
            id=checkpoint_id,
            last_modified=last_modified,
        )
        return info

    def create_checkpoint(self, path):
        if not self.is_bundle(path):
            return self.fm.create_checkpoint(path)

        now = datetime.datetime.now()
        checkpoint_id = now.strftime("%Y-%m-%d %H:%M:%S")
        checkpoint_dir = self._get_checkpoint_dir(path)
        os_checkpoint_dir = self._get_os_path(path=checkpoint_dir)
        if not os.path.exists(os_checkpoint_dir):
            os.mkdir(os_checkpoint_dir)

        bundle = self.get_bundle(path)
        cp_path = self.get_checkpoint_path(checkpoint_id, path)
        os_cp_path = self._get_os_path(cp_path)

        self._copy(bundle.bundle_file, os_cp_path)

        # return the checkpoint info
        return self.get_checkpoint_model(checkpoint_id, path)

    def list_checkpoints(self, path):
        """Return a list of checkpoints for a given notebook"""
        if not self.is_bundle(path):
            return self.fm.list_checkpoints(path)

        path = path.strip('/')

        checkpoint_dir = self._get_checkpoint_dir(path)
        os_checkpoint_dir = self._get_os_path(path=checkpoint_dir)
        if not os.path.exists(os_checkpoint_dir):
            return []

        name = path.rsplit('/', 1)[-1]
        basename, ext = os.path.splitext(name)
        prefix = "{name}---".format(name=basename)

        _, _, files = next(os.walk(os_checkpoint_dir))
        cp_names = [fn for fn in files if fn.startswith(prefix)]
        cp_basenames = map(lambda fn: os.path.splitext(fn)[0], cp_names)
        checkpoint_ids = map(lambda fn: fn.replace(prefix, ''), cp_basenames)
        return [self.get_checkpoint_model(checkpoint_id, path)
                for checkpoint_id in checkpoint_ids]

    def restore_checkpoint(self, checkpoint_id, path=''):
        """Restore a notebook from one of its checkpoints"""
        raise NotImplementedError("must be implemented in a subclass")

    def delete_checkpoint(self, checkpoint_id, path=''):
        """delete a checkpoint for a notebook"""
        raise NotImplementedError("must be implemented in a subclass")


if __name__ == '__main__':
    from nbformat.v4 import new_notebook, writes

    from nbx_deux.testing import TempDir
    with TempDir() as td:
        subdir = td.joinpath('subdir')

        nbm = BundleContentsManager(root_dir=str(td))

        nb = new_notebook()
        nb['metadata']['howdy'] = 'hi'
        model = NotebookModel.from_nbnode(nb, path='hi.ipynb', name='hi.ipynb')

        new_model = nbm.save(model, 'dale.ipynb')
