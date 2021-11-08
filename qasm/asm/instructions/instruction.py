from typing import Union, Tuple, Dict, Deque
from collections import deque

try:
    from .stack_machine import StackState, StackTransformation, Stack, IncompatibleTypesOnStackError
    from ..type import Type, Generic
except ImportError:
    from qasm.asm.instructions.stack_machine import StackState, StackTransformation, Stack, IncompatibleTypesOnStackError
    from qasm.asm.type import Type, Generic


class InvalidInstructionArgumentType(Exception):
    def __init__(self, expected: Type, got: Type):
        super().__init__(f"Expected argument type of {expected}, got {got}")
        self._expected = expected
        self._got = got

    @property
    def expected(self):
        return self._expected

    @property
    def got(self):
        return self._got


class Instruction:
    def __init__(self, name: str, parameters: Union[Tuple[Type, ...], Type], in_: Union[StackTransformation, StackState, Tuple[Type]], out: Union[StackState, Tuple[Type], None] = None):
        if isinstance(parameters, Type):
            parameters = (parameters,)
        if not isinstance(parameters, tuple):
            parameters = tuple(parameters)
        if isinstance(in_, tuple):
            in_ = StackState(*in_)
        if isinstance(out, tuple):
            out = StackState(*out)
        if isinstance(in_, StackTransformation):
            self._transformation = in_
        elif isinstance(in_, StackState):
            if isinstance(out, StackState):
                self._transformation = in_ >> out
            else:
                raise TypeError(f"expected either a \'{StackState.__name__}\' or a \'{tuple.__name__}\', got a \'{type(out).__name__}\'")
        else:
            raise TypeError(f"expected either a \'{StackState.__name__}\', a {StackTransformation.__name__} or a \'{tuple.__name__}\', got a \'{type(out).__name__}\'")
        self._name = name
        self._parameters = parameters

    @property
    def name(self):
        return self._name

    @property
    def parameters(self):
        return self._parameters

    @property
    def transformation(self):
        return self._transformation

    def build_from(self, stack: Stack, *arguments: Type) -> "Instruction":
        if len(arguments) != len(self._parameters):
            raise ValueError(f"Number of arguments is different than the number of parameters")
        types_before: Deque[Type] = deque()
        types_after: Deque[Type] = deque()
        generic_mapping: Dict[str, Type] = {}
        for argument, parameter in zip(arguments, self._parameters):
            try:
                parameter = generic_mapping[parameter.name]
            except KeyError:
                generic_mapping[parameter.name] = argument
            else:
                if argument.name != parameter.name:
                    raise InvalidInstructionArgumentType(parameter, argument)
        for stack_type, type_before in zip(stack.top(len(self._transformation.before.types)), self._transformation.before.types):
            if isinstance(type_before, Generic):
                try:
                    type_before = generic_mapping[type_before.name]
                except KeyError:
                    generic_mapping[type_before.name] = type_before = stack_type
            types_before.append(type_before)
        for stack_type, type_before in zip(reversed(stack), reversed(types_before)):
            if type_before.name != stack_type.name:
                raise IncompatibleTypesOnStackError(
                    types_before,
                    stack.top(len(self._transformation.before.types))
                )
        for type_after in self._transformation.after.types:
            if isinstance(type_after, Generic):
                type_after = generic_mapping[type_after.name]
            types_after.append(type_after)
        return Instruction(self._name, self._parameters, StackState(*types_before), StackState(*types_after))

    def __str__(self) -> str:
        return f"{self._name} {', '.join(map(str, self._parameters))} [{self._transformation}]"


if __name__ == '__main__':
    Int = Type("int")
    Float = Type("float")
    Ptr = Type("ptr")
    String = Type("str")
    Func = Type("function")
    stack = Stack()
    print(1, stack)
    stack.apply(StackState[...] >> StackState[Float, Float])
    print(2, stack)
    stack.apply(StackState[...] >> StackState[Int, Int])
    print(3, stack)
    add = Instruction("add", (), StackState(Generic('T'), Generic('T')), StackState(Generic('T')))
    pop_by_type = Instruction("pop", (Generic('T'), Generic('T')), StackState(Generic('T')), StackState())
    add_int = add.build_from(stack)
    print(4, add_int)
    stack.apply(add_int.transformation)
    stack.apply(StackState[Int] >> StackState[...])
    print(5, stack)
    add_float = add.build_from(stack)
    print(6, add_float)
    stack.apply(add_float.transformation)
    print(7, stack)
    pop_float = pop_by_type.build_from(stack, Float, Float)
    stack.apply(pop_float.transformation)
    print(8, stack)
