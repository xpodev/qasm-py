from typing import Iterable, Optional, Dict

from qasm.asm.old.bin_types import TypeMeta, Type, Pointer
from qasm.asm.old.label import Label


class FieldDefinition(Label):
    def __init__(self, name: str, offset: int, typ: TypeMeta):
        super().__init__(name, offset)
        self._type = typ
        self._owner: Optional[TypeDefinition] = None

    @property
    def type(self):
        return self._type

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self._owner: Optional[TypeDefinition] = value


class TypeDefinition(Type, Label):
    def __init__(self, name: str, offset: int, modifiers: Iterable[str]):
        Label.__init__(self, name, offset)
        self._modifiers = set(modifiers)
        self._fields: Dict[str, FieldDefinition] = {}
        self._size = 0

    @property
    def name(self):
        return self._name

    @classmethod
    def index(cls):
        return Pointer.index()

    @property
    def size(self):
        return self._size

    def add_field(self, name: str, typ: TypeMeta) -> FieldDefinition:
        if name in self._fields:
            raise ValueError(f"Field {name} already exists in type {self.name}")
        field = FieldDefinition(name, self._size, typ)
        self._fields[name] = field
        self._size += typ.size
        return field

    def get_field(self, name: str):
        return self._fields[name]

    @classmethod
    def to_bytes(cls, v: bytes) -> bytes:
        pass

    @classmethod
    def parse(cls, v: str):
        pass

    @classmethod
    def default(cls):
        pass
