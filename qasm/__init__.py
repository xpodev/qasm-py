from functools import reduce
from pathlib import Path

from qasm.asm.assembler import Assembler
from qasm.parsing.parser import default_parser
from qasm.parsing.tokenizer import Tokenizer
from qasm.qpl.file import QPLFlags


def make_flags(*flags: QPLFlags):
    return reduce(QPLFlags.__or__, flags, 0)


def assemble_file(
        input_path: str,
        output_path: str = None,
        file_ext: str = ".qpl",
        flags: QPLFlags = 0):
    output_path = output_path if output_path else Path(input_path).with_suffix(file_ext)
    with open(input_path) as source:
        Assembler().assemble(default_parser(Tokenizer(source.read())).parse(), flags).write(output_path)


if __name__ == '__main__':
    assemble_file("../tests/test1.qsm")
