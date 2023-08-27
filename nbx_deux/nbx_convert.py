from jupytext.formats import (
    _SCRIPT_EXTENSIONS,
)
from nbformat import v4 as current
from jupytext.cell_reader import (
    DoublePercentScriptCellReader,
)
from jupytext.cell_to_text import (
    DoublePercentCellExporter,
)


class NBXCellScriptCellReader(DoublePercentScriptCellReader):
    def __init__(self, fmt=None, default_language=None):
        if fmt is None:
            fmt = {}
        super().__init__(fmt=fmt, default_language=default_language)

    def read(self, lines):
        cell, pos_next_cell = super().read(lines)
        # super call generates a new id. We replace with metadata id
        cell_id = cell.metadata.pop('id')
        cell['id'] = cell_id
        return cell, pos_next_cell


class NBXCellExport(DoublePercentCellExporter):
    """
    CellExporter that assumes cells all have ids.
    """
    def __init__(self, cell, default_language='python', *args, **kwargs):
        kwargs.setdefault('fmt', NBX_FORMAT)
        super().__init__(cell, default_language, *args, **kwargs)
        self.cell_id = cell.id

    def cell_to_text(self):
        self.metadata['id'] = self.cell_id
        return super().cell_to_text()


ext = '.py'
NBX_FORMAT = dict(
    format_name="nbxpercent",
    extension=ext,
    header_prefix=_SCRIPT_EXTENSIONS[ext]["comment"],
    header_suffix=_SCRIPT_EXTENSIONS[ext].get("comment_suffix", ""),
    cell_reader_class=NBXCellScriptCellReader,
    cell_exporter_class=NBXCellExport,
    current_version_number="1.3",
    min_readable_version_number="1.1",
)


def upgrade_nb(nb):
    current_format_tuple = (
        current.nbformat,
        current.nbformat_minor,
    )
    format_tuple = (nb['nbformat'], nb['nbformat_minor'])
    if format_tuple < current_format_tuple:
        current.convert.upgrade(nb)
        return True
    return False


def upgrade_nb_on_file(nb_file):
    with open(nb_file) as f:
        nb = current.reads(f.read())
        upgraded = upgrade_nb(nb)
        if not upgraded:
            return
        with open(nb_file, 'w') as f:
            f.write(current.writes(upgraded))


if __name__ == '__main__':
    ...
