import os

if True:
    from functools import reduce
    from pathlib import Path

    from qasm.asm.old.assembler import Assembler
    from qasm.parsing.old.parser import default_parser
    from qasm.parsing.tokenizer import Tokenizer
    from qasm.qpl.file import QPLFlags, ArchitectureInfo


    def make_flags(*flags: QPLFlags):
        return reduce(QPLFlags.__or__, flags, 0)


    def assemble_file(
            input_path: str,
            output_path: str = None,
            file_ext: str = ".qpl",
            flags: QPLFlags = 0,
            arch: ArchitectureInfo = None,
            cwd: str = None
    ):
        os.chdir(cwd if cwd else Path(input_path).parent)
        with open(input_path) as source:
            Assembler().assemble(default_parser(Tokenizer(source.read())).parse(), flags).write(
                output_path if output_path else Path(input_path).with_suffix(file_ext),
                flags,
                arch if arch else ArchitectureInfo.get_native_architecture_info(),
            )


    if __name__ == '__main__':
        assemble_file("../tests/test1.qsm")
