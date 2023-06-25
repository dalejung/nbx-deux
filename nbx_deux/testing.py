from tempfile import TemporaryDirectory
from pathlib import Path


class TempDir:
    td: TemporaryDirectory
    temp_path: Path | None = None
    keep_open: bool

    def __init__(self, *, keep_open=False):
        self.td = TemporaryDirectory()
        self.keep_open = keep_open

    def set_keep_open(self, keep_open: bool):
        self.keep_open = keep_open

    def __enter__(self):
        self.temp_path = Path(self.td.__enter__())
        return self

    def __exit__(self, exc, value, tb):
        if self.keep_open:
            return
        return self.td.__exit__(exc, value, tb)

    def __getattr__(self, name):
        if self.temp_path and hasattr(self.temp_path, name):
            return getattr(self.temp_path, name)
        raise AttributeError(name)

    def cleanup(self):
        self.td.cleanup()

    def __repr__(self):
        return f"TempDir(temp_path={self.temp_path})"

    def __str__(self):
        return str(self.temp_path)

    def __fspath__(self):
        return str(self.temp_path)

    def __eq__(self, other):
        return Path(self) == Path(other)
