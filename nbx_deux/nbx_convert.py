from nbformat import v4 as current
from jupytext.cell_reader import (
    DoublePercentScriptCellReader,
)
from jupytext.cell_to_text import (
    DoublePercentCellExporter,
)


class NBXCellScriptCellReader(DoublePercentScriptCellReader):
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
    def __init__(self, cell, default_language, *args, **kwargs):
        super().__init__(cell, default_language, *args, **kwargs)
        self.cell_id = cell.id

    def cell_to_text(self):
        self.metadata['id'] = self.cell_id
        return super().cell_to_text()


def upgrade_nb(nb_file):
    with open(nb_file) as f:
        nb = current.reads(f.read())

    current_format_tuple = (
        current.nbformat,
        current.nbformat_minor,
    )
    format_tuple = (nb['nbformat'], nb['nbformat_minor'])
    if format_tuple < current_format_tuple:
        upgraded = current.convert.upgrade(nb)
        with open(nb_file, 'w') as f:
            f.write(current.writes(upgraded))
