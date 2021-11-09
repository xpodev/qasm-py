from collections import deque
from typing import Deque, Optional

from pprint import pprint

try:
    from ..type import *
except ImportError:
    from qasm.asm.type import *


class InvalidStackOperationError(Exception):
    ...


class StackState:
    def __init__(self, *types: Type):
        self._types = unpack_types(types)

    @property
    def types(self):
        return self._types

    def __rshift__(self, other) -> "StackTransformation":
        if not isinstance(other, StackState):
            raise TypeError(f"unsupported operand type(s) for >>: \'{type(self).__name__}\' and \'{type(other).__name__}\'")
        return StackTransformation(self, other)

    def __class_getitem__(cls, item):
        if item is Ellipsis:
            return cls()
        if isinstance(item, Type):
            return cls(item)
        if not isinstance(item, tuple):
            raise TypeError
        if not all(map(lambda x: isinstance(x, Type), item)):
            raise TypeError(f"all items must be instances of \'{Type.__name__}\'")
        return cls(*item)

    def __str__(self):
        return f"Stack[{', '.join(map(str, self._types))}]"


class InvalidStackStateError(InvalidStackOperationError):
    ...


class IncompatibleTypesOnStackError(InvalidStackStateError):
    def __init__(self, expected, got):
        if isinstance(expected, Type):
            expected = expected,
        if isinstance(got, Type):
            got = got,
        super().__init__(f"Expected the stack to be {StackState(*expected)} but it was {StackState(*got)}")
        self._expected = expected
        self._got = got

    @property
    def expected(self):
        return self._expected

    @property
    def got(self):
        return self._got


class NotEnoughValuesError(InvalidStackStateError):
    def __init__(self, expected: int, got: int):
        super().__init__(f"Expected to have at least {expected} items on the stack, but only got {got}")
        self._expected = expected
        self._got = got

    @property
    def expected(self):
        return self._expected

    @property
    def got(self):
        return self._got


class StackTransformation:
    def __init__(self, before: StackState, after: StackState) -> None:
        self._before = before
        self._after = after

    @property
    def before(self) -> StackState:
        return self._before

    @property
    def after(self) -> StackState:
        return self._after

    def __str__(self) -> str:
        return f"[{', '.join(map(str, self._before.types))}] -> [{', '.join(map(str, self._after.types))}]"


class Stack(deque, Deque[Type]):
    def top(self, n: int = 1):
        return tuple(self)[-n:]

    def try_pop_type(self, typ: Type) -> Optional[Type]:
        try:
            if self[-1] != typ:
                return None
            return self.pop()
        except IndexError:
            return None

    def pop_type(self, typ: Type) -> Type:
        top = self.try_pop_type(typ)
        if top is None:
            raise InvalidStackStateError(f"Expected type {typ} but got {self.top()[0]}")
        return top

    def apply(self, transformation: StackTransformation) -> None:
        if not isinstance(transformation, StackTransformation):
            raise TypeError(f"Expected an object of type {StackTransformation.__name__} but got a \'{type(transformation).__name__}\'")
        if len(self) < len(transformation.before.types):
            raise NotEnoughValuesError(len(transformation.before.types), len(self))
        for typ in reversed(transformation.before.types):
            if isinstance(typ, Many):
                if typ.limit < 0:
                    while self.try_pop_type(typ.type):
                        ...
                else:
                    for i in range(typ.limit):
                        self.pop_type(typ.type)
            else:
                self.pop_type(typ)
        self.extend(transformation.after.types)


if __name__ == '__main__':
    Int = Type("int")
    Float = Type("float")
    Ptr = Type("ptr")
    String = Type("str")
    Func = Type("function")
    stack = Stack()
    stack.apply(StackState[...] >> StackState[Int])
    stack.apply(StackState[...] >> StackState[Int])
    stack.apply(StackState[Int[2]] >> StackState[Int[1]])
    stack.apply(StackState[Int] >> StackState[...])
    pprint(stack)
