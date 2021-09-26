import sys
from pathlib import Path

from qasm import assemble_file


def main(path):
    assemble_file(path)


if __name__ == '__main__':
    try:
        filename = sys.argv[1]
    except IndexError:
        custom = False
        # filename = (input("File: ") if custom else False) or "tests/lib.qsm"
        filename = (input("File: ") if custom else False) or "tests/test1.qsm"

        # print("Filename must be supplied")
        # print(f"Usage: {Path(__file__).name} {{filename}}")
    main(Path(filename).resolve())
