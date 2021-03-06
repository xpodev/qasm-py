from typing import Iterable, Tuple

__all__ = [
    "All",
    "Generic",
    "Many",
    "Template",
    "Type",
    "unpack_types"
]


class Type:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __getitem__(self, item):
        if item is Ellipsis:
            item = -1
        if isinstance(item, int):
            if item == 1:
                return self
            return Many(self, item)
        raise TypeError(f"Expected either an 'int' or '...' but got a {type(item).__name__}")

    def __repr__(self):
        return f"{type(self).__qualname__}({self._name:s})"

    def __str__(self) -> str:
        return self._name


class Many(Type):
    def __init__(self, typ: Type, limit: int) -> None:
        self._type = typ
        self._limit = limit
        super().__init__(str(self))

    @property
    def type(self) -> Type:
        return self._type

    @property
    def limit(self) -> int:
        return self._limit

    def __str__(self) -> str:
        return f"{self._type}[{'...' if self._limit < 0 else self._limit}]"


class All(Many):
    def __class_getitem__(cls, item):
        if not isinstance(item, Type):
            raise TypeError(f"Expected an instance of \'{Type.__name__}\', got a \'{type(item).__name__}\'")
        return item[...]


class Generic(Type):
    def __init__(self, name: str):
        super().__init__(f"GenericName<{name}>")

    def __class_getitem__(cls, item) -> "Generic":
        return cls(item)


class Template(Type):
    __slots__ = ("types", )

    def __init__(self, name: str, *types: Type):
        super().__init__(f"TemplateName<{name}>")
        self._types = types

    def __class_getitem__(cls, item) -> "Template":
        return cls(item)


def unpack_types(types: Iterable[Type]) -> Tuple[Type, ...]:
    result = []
    for typ in types:
        if isinstance(typ, Many) and typ.limit >= 0:
            result.extend(unpack_types(typ.type for _ in range(typ.limit)))
        elif isinstance(typ, Template):
            try:
                result.extend(typ.types)
            except AttributeError:
                result.append(typ)
        else:
            result.append(typ)
    return tuple(result)
