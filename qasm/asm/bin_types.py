import sys
import struct

from abc import ABCMeta, abstractmethod, ABC

NATIVE_ORDER = sys.byteorder
NATIVE_SIZE = struct.calcsize("P")
NATIVE_BIT_WIDTH = NATIVE_SIZE * 8
IS_32_BIT = NATIVE_BIT_WIDTH == 32
IS_64_BIT = NATIVE_BIT_WIDTH == 64

__all__ = [
    "AnyOf",
    "Argument",
    "Bytes",
    "Float",
    "Float32",
    "Float64",
    "IS_32_BIT",
    "IS_64_BIT",
    "Int",
    "Int16",
    "Int32",
    "Int64",
    "Int8",
    "Local",
    "NATIVE_BIT_WIDTH",
    "NATIVE_SIZE",
    "Pointer",
    "RelativePointer",
    "String",
    "TYPES",
    "TypeSize",
    "TYPE_INDEX",
    "TYPE_TABLE",
    "Type",
    "TypeMeta",
    "Variable",
    "Void",
    "is_32bit",
    "is_64bit"
]


def is_32bit():
    return IS_32_BIT


def is_64bit():
    return IS_64_BIT


class TypeMeta(ABCMeta):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(cls, "_name"):
            cls._name = None
        if not hasattr(cls, "_size"):
            cls._size = 0

    @abstractmethod
    def index(cls) -> int:
        ...

    @property
    def name(cls) -> str:
        return cls._name

    @property
    def size(cls):
        return cls._size

    @abstractmethod
    def to_bytes(cls, v) -> bytes:
        ...

    @abstractmethod
    def parse(cls, v: str):
        ...

    def __str__(self):
        return self.name

    def __or__(cls, other):
        if not isinstance(Type, TypeMeta):
            raise TypeError(f"invalid operand type '|' for types: {type(cls)} and {type(other)}")
        if isinstance(cls, AnyOf):
            return AnyOf(*cls.types, other)
        return AnyOf(cls, other)


class Type(metaclass=TypeMeta):
    _name: str = "type"

    @classmethod
    def index(cls):
        return TYPE_INDEX[cls._name]

    @classmethod
    @abstractmethod
    def to_bytes(cls, v) -> bytes:
        ...

    @classmethod
    @abstractmethod
    def parse(cls, v: str):
        ...

    @classmethod
    @abstractmethod
    def default(cls):
        ...


class Variable(Type):
    _name = "var"

    @classmethod
    def get_type_by_value(cls, v) -> TypeMeta:
        typ = type(v)
        if v is None:
            return Void
        if issubclass(typ, str):
            return String
        if issubclass(typ, bool):
            return Bool
        if issubclass(typ, int):
            return Int
        if issubclass(typ, float):
            return Float
        if issubclass(typ, bytes):
            return Bytes
        if issubclass(typ, Pointer):
            return Pointer
        if isinstance(typ, TypeMeta):
            return typ
        raise TypeError(typ)

    @classmethod
    def to_bytes(cls, v):
        return cls.get_type_by_value(v).to_bytes(v)

    @classmethod
    def parse(cls, v: str):
        raise TypeError

    @classmethod
    def default(cls):
        raise TypeError(f"Variable type doesn't have a default value")


class AnyOf(Variable):
    _name = "::any_of"

    def __init__(self, *types: TypeMeta):
        self._types = set(types)

    @property
    def types(self):
        return self._types

    def __or__(self, other):
        if not isinstance(Type, TypeMeta):
            raise TypeError(f"invalid operand type '|' for types: {type(self)} and {type(other)}")
        return AnyOf(*self._types, other)

    def __str__(self):
        return ' | '.join(map(str, self._types))


class Void(Type):
    _name = "void"
    _size = 0

    @classmethod
    def to_bytes(cls, v) -> bytes:
        return b""

    @classmethod
    def parse(cls, v: str):
        return None

    @classmethod
    def default(cls):
        return None


class Int(Type):
    _size = NATIVE_SIZE
    _name = "int"

    @classmethod
    def to_bytes(cls, v: int):
        return v.to_bytes(cls._size, NATIVE_ORDER, signed=v < 0)

    @classmethod
    def from_bytes(cls, b: bytes):
        return int.from_bytes(b, NATIVE_ORDER, signed=True)

    @classmethod
    def parse(cls, v: str):
        return int(v)

    @classmethod
    def default(cls):
        return 0


class Bool(Int):
    _size = 1
    _name = "bool"

    @classmethod
    def to_bytes(cls, v: bool):
        return v.to_bytes(1, NATIVE_ORDER)

    @classmethod
    def parse(cls, v: str):
        return {
            "true": True,
            "false": False
        }[v]


class Int8(Int):
    _size = 1
    _name = "int8"


class Int16(Int):
    _size = 2
    _name = "int16"


class Int32(Int):
    _size = 4
    _name = "int32"


class Int64(Int):
    _size = 8
    _name = "int64"


class TypeSize(Int):
    _name = "sizeof"


class Pointer(Type):
    _name = "ptr"
    _type = None
    _size = NATIVE_SIZE

    @classmethod
    def type(cls):
        return cls._type

    @classmethod
    def to_bytes(cls, v: int):
        return v.to_bytes(NATIVE_SIZE, NATIVE_ORDER)

    @classmethod
    def from_bytes(cls, v: bytes):
        return int.from_bytes(v, NATIVE_ORDER)

    @classmethod
    def parse(cls, v: str):
        return int(v)

    @classmethod
    def default(cls):
        return 0

    def __class_getitem__(cls, item):
        return type(cls)(cls.__name__, (cls, *cls.__bases__), {
            **cls.__dict__,
            "_type": item
        })


class RelativePointer(Pointer):
    _name = "rptr"

    @classmethod
    def to_bytes(cls, v: int):
        return v.to_bytes(NATIVE_SIZE, NATIVE_ORDER, signed=True)

    @classmethod
    def from_bytes(cls, v: bytes):
        return int.from_bytes(v, NATIVE_ORDER, signed=True)


class Bytes(Pointer):
    _name = "raw"

    @classmethod
    def to_bytes(cls, v: bytes):
        return v

    @classmethod
    def from_bytes(cls, v: bytes):
        return v

    @classmethod
    def parse(cls, v: str):
        return v.encode("ascii")

    @classmethod
    def default(cls):
        return b""


class String(Bytes):
    _name = "str"

    @classmethod
    def to_bytes(cls, v: str):
        return super().to_bytes(v.encode("ascii"))

    @classmethod
    def from_bytes(cls, v: bytes):
        return v.decode("ascii")

    @classmethod
    def parse(cls, v: str):
        return v

    @classmethod
    def default(cls):
        return ""


class Float(Type):
    _name = "float"
    _size = NATIVE_SIZE

    @classmethod
    def to_bytes(cls, v: float):
        if IS_32_BIT:
            return Float32.to_bytes(v)
        elif IS_64_BIT:
            return Float64.to_bytes(v)
        raise ValueError(f"Invalid system architecture \'{NATIVE_BIT_WIDTH} bits\'")

    @classmethod
    def from_bytes(cls, v: bytes) -> float:
        if IS_32_BIT:
            return Float32.from_bytes(v)
        elif IS_64_BIT:
            return Float64.from_bytes(v)
        raise ValueError(f"Invalid system architecture \'{NATIVE_BIT_WIDTH} bits\'")

    @classmethod
    def parse(cls, v: str):
        return float(v)

    @classmethod
    def default(cls):
        return 0.0


class Float32(Float):
    _name = "float32"
    _struct = struct.Struct("f")
    _size = _struct.size

    @classmethod
    def to_bytes(cls, v: float):
        return cls._struct.pack(v)

    @classmethod
    def from_bytes(cls, v: bytes) -> float:
        return cls._struct.unpack(v)[0]


class Float64(Float):
    _name = "float64"
    _struct = struct.Struct("d")
    _size = _struct.size

    @classmethod
    def to_bytes(cls, v: float):
        return cls._struct.pack(v)

    @classmethod
    def from_bytes(cls, v: bytes) -> float:
        return cls._struct.unpack(v)[0]


class Local(Int8):
    _name = "local"


class Argument(Int8):
    _name = "arg"


T_VOID = Void.name

T_POINTER = Pointer.name
T_RELATIVE_POINTER = RelativePointer.name

T_INT = Int.name
T_BOOL = Bool.name
T_INT8 = Int8.name
T_INT16 = Int16.name
T_INT32 = Int32.name
T_INT64 = Int64.name

T_FLOAT = Float.name
T_FLOAT32 = Float32.name
T_FLOAT64 = Float64.name

T_RAW = Bytes.name
T_STRING = String.name

T_LOCAL = Local.name
T_ARGUMENT = Argument.name

TYPES = [
    None,
    Void,
    Bool,
    Pointer,
    RelativePointer,
    Int,
    Int8,
    Int16,
    Int32,
    Int64,
    Float,
    Float32,
    Float64,
    String,
    Bytes,
    Local,
    Argument
]

TYPE_TABLE = {
    t.name: t for t in TYPES[1:]
}

TYPE_INDEX = {
    key.name: i for i, key in enumerate(TYPES[1:], start=1)
}

if __name__ == '__main__':
    _T_STRING = String()
    _T_BYTES = Bytes()

    _T_INT_NATIVE = Int()

    _T_INT_8 = Int8()
    _T_INT_16 = Int16()
    _T_INT_32 = Int32()
    _T_INT_64 = Int64()

    _T_FLOAT_NATIVE = Float()

    _T_FLOAT_32 = Float32()
    _T_FLOAT_64 = Float64()

    _T_BOOL = Bool()

    _T_POINTER = Pointer()

    _T_VOID = Void()

    for typename, idx in TYPE_INDEX.items():
        typ = TYPE_TABLE[typename]
        print(f"[{idx}] => {typ.__name__} as {typ.name} ({typ.size} bytes)")
