from functools import cached_property
from pathlib import Path
from typing import cast
import copy

from nbformat import NotebookNode


from nbx_deux.nb_model import (
    NBSection,
    NBOutput,
    NBOutputType,
)


class NormalizedNotebookPy:
    def __init__(self, notebooknode: NotebookNode):
        self.notebooknode = notebooknode
        self.cell_map = {cell['id']: cell for cell in notebooknode['cells']}

    def get_pyheader(self, cell):
        bits = []

        cell_type = cell['cell_type']
        if cell_type != 'code':
            cell_type_bit = f"[{cell_type}]"
            bits.append(cell_type_bit)

        bits.append(f"id={cell['id']}")
        metadata = " ".join(bits)

        header = f"# %% {metadata}"
        return header

    @cached_property
    def components(self):
        # gonna pare down skeleton by removing source / outputs
        skeleton = copy.deepcopy(self.notebooknode)
        source_cells = {}
        all_outputs = {}

        for cell in skeleton['cells']:
            id = cell['id']
            source_cells[id] = {
                'id': id,
                'cell_type': cell['cell_type'],
                'source': cell.pop('source'),
            }

            if outputs := cell.pop('outputs', None):
                sentinel_outputs = []
                for output in outputs:
                    sentinel = {
                        'output_type': output['output_type'],
                    }
                    sentinel_outputs.append(sentinel)
                cell['outputs'] = sentinel_outputs
                all_outputs[id] = outputs

        return {
            'skeleton': skeleton,
            'source_cells': source_cells,
            'all_outputs': all_outputs
        }

    def munge_source(self, source):
        source = source.strip()

        if source.startswith('%%'):
            source = f'"""\n{source}\n"""'
            return source

        lines = []
        for line in source.split('\n'):
            if line.startswith('!') or line.startswith('%'):
                line = f"# |{line}|"
            lines.append(line)

        source = '\n'.join(lines)
        return source


    def to_pyfile(self):
        outs = []
        for id, cell in self.components['source_cells'].items():
            cell_type = cell['cell_type']
            source = cell['source']

            source = self.munge_source(source)
            if not source.strip():
                continue

            header = self.get_pyheader(cell)

            out = ""
            match cell_type:
                case 'code':
                    out = f"{header}\n\n{source}"
                case 'markdown':
                    out = f'{header}\n\n"""\n{source}\n"""'
                case _:
                    raise Exception(f"Dunno how to handle this {cell_type=}")

            outs.append(out)

        return "\n\n".join(outs)


def notebooknode_to_nnpy(nb_node: NotebookNode):
    return NormalizedNotebookPy(nb_node)


def parse_nnpy_header(line):
    if not line.startswith('# %%'):
        return

    info = {}
    bits = line[4:].split(' ')
    for bit in bits:
        if not bit.strip():
            continue
        if bit.startswith('[') and bit.endswith(']'):
            info['cell_type'] = bit[1:-1]

        try:
            k, v = bit.split('=')
            info[k] = v
        except Exception:
            pass

    # default to code
    if 'cell_type' not in info:
        info['cell_type'] = 'code'

    # we require at least id/cell_type
    if not {'id'}.issubset(set(info.keys())):
        return

    return info


def nnpy_to_sections(content):
    lines = content.splitlines()
    sections = {}
    section = None
    for line in lines:
        header = parse_nnpy_header(line)
        if header:
            section = sections.setdefault(header['id'], NBSection(**header))
        else:
            if section is None:
                raise Exception(f"File did not start with header {line}")
            section.append(line)
    return sections
