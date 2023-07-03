from enum import StrEnum, auto
from nbformat.validator import get_validator

class NBOutputType(StrEnum):
    EXECUTE_RESULT = auto()
    DISPLAY_DATA = auto()
    STREAM = auto()
    ERROR = auto()


class NBSection:
    def __init__(self, id, cell_type):
        self.id = id
        self.cell_type = cell_type
        self.lines = []

    def append(self, line):
        self.lines.append(line)

    def __repr__(self):
        return f"NBSection(id={self.id}, cell_type={self.cell_type})"


class NBOutput:
    def __init__(self, output_type):
        self.output_type = output_type


if __name__ == '__main__':
    validator = get_validator()
    schema = validator._schema
    definitions = schema['definitions']
