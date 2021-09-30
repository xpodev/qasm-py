from typing import Iterable

from qasm.asm.old.instructions import InstructionDefinition
from qasm.asm.old.bin_types import TypeMeta


__all__ = [
    "InstructionArgument",
    "Instruction"
]


class InstructionArgument:
    def __init__(self, typ: TypeMeta, value):
        self._type = typ
        self._value = value

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value


class Instruction:
    def __init__(self, instruction: InstructionDefinition, arguments: Iterable[InstructionArgument], offset: int):
        self._instruction = instruction
        self._arguments = arguments
        self._offset = offset

    @property
    def instruction(self):
        return self._instruction

    @property
    def opcode(self):
        return self._instruction.code

    @property
    def opname(self):
        return self._instruction.name

    @property
    def parameters(self):
        return self._instruction.types

    @property
    def arguments(self):
        return self._arguments

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: int):
        self._offset = value

    def to_bytes(self, *types: TypeMeta) -> bytes:
        return self._instruction.to_bytes(types if types else tuple(map(lambda arg: arg.type, self._arguments)), *tuple(map(lambda x: x.value, self._arguments)))
