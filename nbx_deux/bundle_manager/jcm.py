from typing import Protocol, runtime_checkable


@runtime_checkable
class ContentsManagerProtocol(Protocol):
    def get(self, path, content=True, type=None, format=None):
        ...

    def save(self, model, path):
        ...

    def delete_file(self, path):
        ...

    def rename_file(self, old_path, new_path):
        ...

    def file_exists(self, path) -> bool:
        ...

    def dir_exists(self, path) -> bool:
        ...

    def is_hidden(self, path) -> bool:
        ...
