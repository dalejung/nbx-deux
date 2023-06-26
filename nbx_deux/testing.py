from tempfile import TemporaryDirectory
from pathlib import Path

from mock import Mock
import pandas as pd


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


def makeFakeGist():
    gist = Mock()
    gist.description = "Test Gist #notebook #pandas #woo"
    gist.id = 123
    # fake files
    filenames = ['a.ipynb', 'b.ipynb', 'test.txt']
    files = {}
    for fn in filenames:
        fo = Mock()
        fo.filename = fn
        fo.content = fn+" content"
        files[fn] = fo

    gist.files = files
    # fake history
    history = []
    dates = pd.date_range("2000", freq="D", periods=4).to_pydatetime()
    for i, date in enumerate(dates):
        state = Mock()
        state.version = i
        state.committed_at = date
        raw_data = {}
        files = {}
        for fn in filenames:
            fo = {
                'content': "{fn}_{i}_revision_content".format(fn=fn, i=i),
                'filename': fn,
            }
            files[fn] = fo
        # after 2, don't include 'a.ipynb'
        if i >= 2:
            del files['a.ipynb']

        raw_data['files'] = files
        state.raw_data = raw_data
        history.append(state)

    gist.history = history

    return gist
