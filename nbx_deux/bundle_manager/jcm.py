from typing import Protocol, runtime_checkable
from nbx_deux.nbx_manager import ApiPath


@runtime_checkable
class ContentsManagerProtocol(Protocol):
    def get(self, path: ApiPath, content=True, type=None, format=None):
        ...

    def save(self, model, path: ApiPath):
        ...

    def delete_file(self, path: ApiPath):
        ...

    def rename_file(self, old_path: ApiPath, new_path: ApiPath):
        ...

    def file_exists(self, path: ApiPath) -> bool:
        ...

    def dir_exists(self, path: ApiPath) -> bool:
        ...

    def is_hidden(self, path: ApiPath) -> bool:
        ...

    # Checkpoints api
    def create_checkpoint(self, path: ApiPath):
        ...

    def list_checkpoints(self, path: ApiPath):
        ...

    def restore_checkpoint(self, checkpoint_id, path: ApiPath):
        ...

    def delete_checkpoint(self, checkpoint_id, path: ApiPath):
        ...
