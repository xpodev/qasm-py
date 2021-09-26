from typing import Iterable

from qasm.parsing.asm_token import Token


class Node:
    ...


class CommentNode(Node):
    def __init__(self, text: str):
        self._text = text

    @property
    def text(self):
        return self._text

    def __str__(self):
        return f";{self._text}"


class DirectiveNode(Node):
    _directive_name: str = ""

    @classmethod
    def directive_name(cls):
        return cls._directive_name

    def __str__(self):
        return f".{self._directive_name}"


class SectionNode(DirectiveNode):
    _directive_name = "section"

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"{super().__str__()} {self._name}"


class LabelNode(DirectiveNode):
    _directive_name = "label"

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self):
        return self._name

    def __str__(self):
        return f"{super().__str__()} {self._name}"


class ParameterNode(Node):
    def __init__(self, name: str, typ: str):
        self._name = name
        self._type = typ

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    def __str__(self):
        return f"{self._type} {self._name}"


class FunctionDefinitionNode(LabelNode):
    _directive_name = "func"

    def __init__(self, name: str, return_type: str, parameters: Iterable[ParameterNode], modifiers: Iterable[str]):
        super().__init__(name)
        self._name = name
        self._return_type = return_type
        self._parameters = tuple(parameters)
        self._modifiers = set(modifiers)

    @property
    def name(self):
        return self._name

    @property
    def return_type(self):
        return self._return_type

    @property
    def parameters(self):
        return self._parameters

    @property
    def modifiers(self):
        return self._modifiers

    def __str__(self):
        return f"{super().__str__()} {self._name} ({', '.join(map(str, self._parameters))}) {' '.join(self._modifiers)}"


class VariableDefinitionNode(LabelNode):
    _directive_name = "var"

    def __init__(self, typename: str, name: str):
        super().__init__(name)
        self._type = typename

    @property
    def type(self):
        return self._type


class InstructionNode(Node):
    class InstructionArgument:
        def __init__(self, value: Token, type_information: str = None):
            self._value = value
            self._type = type_information

        @property
        def value(self):
            return self._value

        @property
        def type(self):
            return self._type

        def __str__(self):
            return f"{self._type} {self._value}" if self._type else str(self._value)

    def __init__(self, opname: str, arguments: Iterable[InstructionArgument]):
        self._opname = opname
        self._arguments = tuple(arguments)

    @property
    def opname(self):
        return self._opname

    @property
    def arguments(self):
        return self._arguments

    def __str__(self):
        return f"{self._opname} {', '.join(map(str, self._arguments))}"


class TypeDefinitionNode(LabelNode):
    _directive_name = "type"

    def __init__(self, name: str, modifiers: Iterable[str]):
        super().__init__(name)
        self._modifiers = set(modifiers)

    @property
    def modifiers(self):
        return self._modifiers

    def __str__(self):
        return f"{super().__str__()} {self.name} {' '.join(self._modifiers)}"
