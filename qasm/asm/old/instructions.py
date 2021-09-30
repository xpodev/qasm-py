import sys
from typing import Dict

from qasm.asm.old.bin_types import *


__all__ = [
    "InstructionDefinition",
    "INSTRUCTIONS",
    "add"
]


class InstructionDefinition:
    OPCODE_SIZE = 1
    ORDER = sys.byteorder

    def __init__(self, name: str, code: int, *operand_types: TypeMeta):
        self._name = name
        self._code = code
        self._operand_types = operand_types

    @property
    def name(self):
        return self._name

    @property
    def code(self):
        return self._code

    @property
    def types(self):
        return self._operand_types

    def to_bytes(self, types, *args):
        assert len(types) == len(args)
        return bytes([
            *self._code.to_bytes(self.OPCODE_SIZE, self.ORDER, signed=True),
            *b"".join(map(lambda x: x[0].to_bytes(x[1]), zip(types, args)))
        ])

    def get_size(self, *types: TypeMeta):
        return self.OPCODE_SIZE + sum(map(lambda t: t.size, types if types else self._operand_types))


INSTRUCTIONS: Dict[str, InstructionDefinition] = {

}


def add(inst: InstructionDefinition):
    INSTRUCTIONS[inst.name] = inst


def setup():
    # code section
    add(InstructionDefinition("nop", 0))
    add(InstructionDefinition("dlog", 1, Type))

    add(InstructionDefinition("push", 2, Variable))
    add(InstructionDefinition("pop", 3, Variable))

    add(InstructionDefinition("call", 4, RelativePointer))
    add(InstructionDefinition("unsafe_call", 5, RelativePointer))
    add(InstructionDefinition("ret", 6))

    add(InstructionDefinition("jmp", 7, RelativePointer))
    add(InstructionDefinition("jmp_true", 8, RelativePointer))
    add(InstructionDefinition("jmp_false", 9, RelativePointer))

    add(InstructionDefinition("cmp_gt", 10, Type, Type))
    add(InstructionDefinition("cmp_lt", 11, Type, Type))
    add(InstructionDefinition("cmp_ge", 12, Type, Type))
    add(InstructionDefinition("cmp_le", 13, Type, Type))
    add(InstructionDefinition("cmp_eq", 14, Type, Type))
    add(InstructionDefinition("cmp_ne", 15, Type, Type))

    add(InstructionDefinition("add", 16, Type, Type))
    add(InstructionDefinition("sub", 17, Type, Type))
    add(InstructionDefinition("mul", 18, Type, Type))
    add(InstructionDefinition("div", 19, Type, Type))
    add(InstructionDefinition("mod", 20, Type, Type))

    add(InstructionDefinition("push_mem", 21, Type, Type))
    add(InstructionDefinition("pop_mem", 22, Type, Type))

    add(InstructionDefinition("new", 23, TypeSize, Int))
    add(InstructionDefinition("free", 24))

    add(InstructionDefinition("dup", 25))

    add(InstructionDefinition("exit", -1))

    # add(InstructionDefinition("dlog", -2))


setup()


if __name__ == '__main__':
    for inst_name, inst in INSTRUCTIONS.items():
        print(f"[{inst.code}] => {inst_name} ({', '.join(map(str, inst.types))})")
