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
from tornado.web import HTTPError

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

    def delete(self, path):
        """Delete a file/directory and any associated checkpoints."""
        path = path.strip("/")
        if not path:
            raise HTTPError(400, "Can't delete root")
        self.delete_file(path)
        # Not sure why ContentsManager was directly accessing .checkpoints
        self.delete_all_checkpoints(path)
        self.emit(data={"action": "delete", "path": path})

    def rename(self, old_path, new_path):
        """Rename a file and any checkpoints associated with that file."""
        self.rename_file(old_path, new_path)
        # Not sure why ContentsManager was directly accessing .checkpoints
        self.rename_all_checkpoints(old_path, new_path)
        self.emit(data={"action": "rename", "path": new_path, "source_path": old_path})

    def update(self, model, path):
        """Update the file's path

        For use in PATCH requests, to enable renaming a file without
        re-uploading its contents. Only used for renaming at the moment.
        """
        path = path.strip("/")
        new_path = model.get("path", path).strip("/")
        if path != new_path:
            self.rename(path, new_path)
        model = self.get(new_path, content=False)
        return model

    def delete_all_checkpoints(self, path):
        self.checkpoints.delete_all_checkpoints(path)

    def rename_all_checkpoints(self, old_path, new_path):
        self.checkpoints.rename_all_checkpoints(old_path, new_path)
