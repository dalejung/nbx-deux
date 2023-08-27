from nbx_deux.nbx_convert import NBXCellExport

from nbx_deux.normalized_notebook import NBXNotebookExport, nbxpy_to_cells
from textwrap import dedent
from nbformat import v4 as current

cython_source = dedent("""
%%cython
from cpython.ref cimport PyObject # somewhere at the top

cdef class RecordCython:
    cdef name
    cdef int age

    def __cinit__(self, name: str, age: int):
        self.name = name
        self.age = age
""").strip()


def test_nbx_export_py():
    cell = current.new_code_cell(
        id='cython_cell',
        source=cython_source,
    )
    nb = current.new_notebook(cells=[cell])

    nnpy = NBXNotebookExport(nb)
    export_text = nnpy.to_pyfile()
    assert export_text.startswith('# %% language="cython"')

    exp = NBXCellExport(cell, 'python')
    assert exp.cell_id == 'cython_cell'
    assert exp.language == 'cython'
    text = exp.cell_to_text()
    # all non python lines are commented out
    for line in text:
        assert line.startswith('#')


def test_nbxpy_to_cell():
    cell = current.new_code_cell(
        id='cython_cell',
        source=cython_source,
    )
    nb = current.new_notebook(cells=[cell])
    nnpy = NBXNotebookExport(nb)
    export_text = nnpy.to_pyfile()

    # reimport the nbx export and re export it.
    # NOTE: import_cells won't be equal to the original cells because the
    # `%% cython` turning the cell into language=cython happens after first export
    import_cells = nbxpy_to_cells(export_text)
    new_nb = current.new_notebook(cells=import_cells)
    new_nnpy = NBXNotebookExport(new_nb)
    assert new_nnpy.to_pyfile() == export_text


if __name__ == '__main__':
    ...
