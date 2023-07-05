from textwrap import dedent

from nbformat import v4 as current

from ..nbx_convert import (
    NBXCellExport,
    NBXCellScriptCellReader,
    upgrade_nb,
)


def test_upgrade_nb():
    nb = current.new_notebook(nbformat=4, nbformat_minor=2)
    cell = current.new_code_cell()
    del cell['id']
    nb.cells.append(cell)
    assert 'id' not in nb['cells'][0]
    upgraded = upgrade_nb(nb)
    cell_id = nb['cells'][0]['id']
    assert upgraded
    assert cell_id is not None
    # already upgraded
    upgraded = upgrade_nb(nb)
    # no need to upgrade
    assert not upgraded
    # cell id did not change
    assert nb['cells'][0]['id'] == cell_id


def test_cell_export():
    cell = current.new_code_cell("import os")
    cell_id = cell['id']
    exp = NBXCellExport(cell)
    code_text = exp.cell_to_text()
    assert code_text == [
        f'# %% id="{cell_id}"',
        'import os'
    ]

    md_cell = current.new_markdown_cell("# header1\n## header2")
    md_cell['id'] = 'daleid'
    md_exp = NBXCellExport(md_cell)
    md_text = md_exp.cell_to_text()
    assert md_text == [
        '# %% [markdown] id="daleid"',
        '# # header1',
        '# ## header2',
    ]


def test_cell_reader():
    source = dedent("""
    # %% id="codeid"
    import os

    # %% [markdown] id="daleid"
    # # header1
    # ## header2
    """).strip()
    lines = source.split("\n")

    reader = NBXCellScriptCellReader()
    cell1, pos_next_cell = reader.read(lines)
    lines = lines[pos_next_cell:]
    cell2, pos_next_cell = reader.read(lines)
    # we reached end
    assert pos_next_cell >= len(lines)

    assert cell1['id'] == 'codeid'
    assert cell1['source'] == 'import os'
    assert cell1['cell_type'] == 'code'

    assert cell2['id'] == 'daleid'
    assert cell2['source'] == '# header1\n## header2'
    assert cell2['cell_type'] == 'markdown'
