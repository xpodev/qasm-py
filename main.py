import sys
from pathlib import Path

from qasm import assemble_file, QPLFlags


def main(path):
    assemble_file(path, flags=QPLFlags.HasEntryPoint)


if __name__ == '__main__':
    try:
        filename = sys.argv[1]
    except IndexError:
        custom = False
        # filename = (input("File: ") if custom else False) or "tests/lib.qsm"
        # filename = (input("File: ") if custom else False) or "tests/test1.qsm"
        # filename = (input("File: ") if custom else False) or "tests/stdlib.qsm"
        # filename = (input("File: ") if custom else False) or "tests/string.qsm"
        # filename = (input("File: ") if custom else False) or "tests/test.qsm"

        parent = Path("tests").resolve()

        for filename in ["test2.qsm"] or ["stdlib.qsm", "string.qsm", "test.qsm"]:
            main(parent / filename)

        # print("Filename must be supplied")
        # print(f"Usage: {Path(__file__).name} {{filename}}")
    else:
        main(Path(filename).resolve())
