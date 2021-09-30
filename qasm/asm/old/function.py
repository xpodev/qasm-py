from typing import Iterable, Dict, Collection
from functools import wraps

from qasm.asm.old.bin_types import TypeMeta
from qasm.asm.old.instruction import Instruction
from qasm.asm.old.label import Label


__all__ = [
    "Function",
    "FunctionModifiers",
    "FunctionReference",
    "Parameter"
]


def _modifier_property(modifier: str):

    def wrapper(func):
        @wraps(func)
        def getter(self):
            return modifier in self._modifiers

        @wraps(func)
        def setter(self, value):
            if type(value) is not bool:
                raise TypeError("value must be a boolean")
            if value:
                self._modifiers.add(modifier)
            else:
                self._modifiers.discard(modifier)

        prop = property(getter, setter)

        return prop
    return wrapper


class FunctionModifiers:
    Export = "export"
    External = "external"


class Parameter:
    def __init__(self, name: str, typ: TypeMeta, index: int):
        self._name = name
        self._type = typ
        self._index = index

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def index(self):
        return self._index


class FunctionReference(Label):
    def __init__(self, name: str, offset: int, return_type: TypeMeta, parameters: Collection[TypeMeta], num_locals: int):
        super().__init__(name, offset)
        self._return_type = return_type
        self._parameter_types = parameters
        self._num_locals = num_locals

    @property
    def return_type(self):
        return self._return_type

    @property
    def parameter_types(self):
        return self._parameter_types

    @property
    def num_params(self):
        return len(self._parameter_types)

    @property
    def num_locals(self):
        return self._num_locals


class Function(FunctionReference):
    def __init__(self, name: str, offset: int, return_type: TypeMeta, parameters: Dict[str, Parameter], locals_: Dict[str, Parameter], body: Iterable[Instruction] = None, modifiers: Iterable[str] = None):
        super().__init__(name, offset, return_type, tuple(map(lambda x: x.type, parameters.values())), len(locals_))
        self._parameters = parameters
        self._body = body or []
        self._locals = locals_
        self._modifiers = modifiers or set()

    @property
    def parameters(self):
        return self._parameters

    @property
    def body(self):
        return self._body

    @property
    def locals(self):
        return self._locals

    @property
    def modifiers(self):
        return tuple(self._modifiers)

    @property
    def num_locals(self):
        return len(self._locals)

    def has_modifier(self, modifier: str):
        return modifier in self._modifiers

    @_modifier_property(FunctionModifiers.External)
    def is_external(self):
        ...

    @_modifier_property(FunctionModifiers.Export)
    def is_exported(self):
        ...
