from io import BytesIO
from struct import pack
from typing import BinaryIO, Collection, Dict

from qasm.asm.old.bin_types import Void, TYPES, TypeMeta, Int

from qasm.asm.old.function import FunctionReference


__all__ = [
    "ExportTable",
    "ExportTableEntry"
]


class ExportTableEntry(FunctionReference):
    def __init__(self, name: str, offset: int, return_type: TypeMeta, parameters: Collection[TypeMeta], num_locals: int):
        super().__init__(name, offset, return_type, parameters, num_locals)

    def to_bytes(self):
        return self._name.encode("ascii") + b'\0' + pack(
            f"P b {self.num_params}b b b",
            self._offset,
            self._return_type.index(),
            *tuple(map(lambda x: x.index(), self.parameter_types)),
            Void.index(),
            self.num_locals
        )

    @classmethod
    def from_binary_io(cls, io: BinaryIO):
        name = []
        while True:
            char = io.read(1)
            if char == b'\0':
                break
            name.append(char)
        name = b"".join(name).decode("ascii")
        offset = Int.from_bytes(io.read(Int.size))
        return_type = TYPES[Int.from_bytes(io.read(1))]
        parameters = []
        while True:
            parameter = TYPES[Int.from_bytes(io.read(1))]
            if parameter is Void:
                break
            parameters.append(parameter)
        num_locals = Int.from_bytes(io.read(1))
        return cls(name, offset, return_type, parameters, num_locals)

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.from_binary_io(BytesIO(data))


class ExportTable:
    def __init__(self):
        self._exports: Dict[str, FunctionReference] = {}

    def add_export(self, export: FunctionReference):
        if export.name in self._exports:
            raise KeyError(f"Function \"{export.name}\" is already exported")
        self._exports[export.name] = export

    def get_export(self, name: str):
        return self._exports[name]

    def to_bytes(self):
        return b"".join([
            Int.to_bytes(len(self._exports)),
            *tuple(map(
                ExportTableEntry.to_bytes, self._exports.values()
            ))
        ])

    @classmethod
    def from_binary_io(cls, io: BinaryIO):
        table = cls()
        num_exports = Int.from_bytes(io.read(Int.size))
        for i in range(num_exports):
            table.add_export(ExportTableEntry.from_binary_io(io))
        return table

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.from_binary_io(BytesIO(data))
