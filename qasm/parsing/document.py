from enum import Enum
from typing import Iterable, Tuple, FrozenSet, Optional, List

try:
    from .itokenizer import Token
except ImportError:
    from qasm.parsing.itokenizer import Token


def assert_type(item, typ: type, parameter_name: str = "item") -> None:
    if not isinstance(item, typ):
        raise TypeError(f"{parameter_name} must be of type {typ.__name__}")


__all__ = [
    "Document",
    "FunctionDeclaration",
    "FunctionDefinition",
    "ImportDeclaration",
    "ImportStatement",
    "ImportType",
    "Instruction",
    "InstructionArgument",
    "Parameter",
    "Pointer",
    "Type",
    "TypeDeclaration",
    "TypeDefinition",
    "VariableDeclaration",
    "VariableDefinition"
]


class ImportType(Enum):
    Function = "function"
    Type = "type"
    Variable = "variable"


class Declaration:
    def __init__(self, keyword: Token, name: Token) -> None:
        self._keyword = keyword
        self._name = name

    @property
    def keyword(self) -> Token:
        return self._keyword

    @property
    def name(self) -> Token:
        return self._name


class ImportDeclaration(Declaration):
    def __init__(self, keyword: Token, name: Token, typ: ImportType) -> None:
        super().__init__(keyword, name)
        self._import_type = typ

    @property
    def import_type(self) -> ImportType:
        return self._import_type


class Type:
    def __init__(self, name: Token) -> None:
        self._name = name

    @property
    def name(self) -> Token:
        return self._name


class Pointer(Type):
    def __init__(self, typ: Type, specifier: Token):
        super().__init__(typ.name)
        self._specifier = specifier

    @property
    def specifier(self):
        return self._specifier


class Parameter:
    def __init__(self, name: Optional[Token], type_name: Type) -> None:
        self._name = name
        self._type = type_name

    @property
    def name(self) -> Token:
        return self._name

    @property
    def type_name(self) -> Type:
        return self._type


class FunctionDeclaration(Declaration):
    declaration_keyword = "func"

    def __init__(self, keyword: Token, name: Token, parameters: Iterable[Parameter], return_type_name: Type) -> None:
        super().__init__(keyword, name)
        self._parameters = tuple(parameters)
        self._return_type = return_type_name

    @property
    def parameters(self) -> Tuple[Parameter, ...]:
        return self._parameters

    @property
    def return_type_name(self) -> Type:
        return self._return_type


class TypeDeclaration(Declaration):
    declaration_keyword = "type"

    def __init__(self, keyword: Token, name: Token):
        super().__init__(keyword, name)


class VariableDeclaration(Declaration):
    declaration_keyword = "var"

    def __init__(self, keyword: Token, name: Token, type_name: Type) -> None:
        super().__init__(keyword, name)
        self._type = type_name

    @property
    def type(self) -> Type:
        return self._type


class ImportStatement:
    declaration_keyword = "import"

    def __init__(self, keyword: Token, file: Token, modifiers: Iterable[Token]) -> None:
        self._keyword = keyword
        self._file = file
        self._modifiers = frozenset(modifiers)
        self._imports = []

    @property
    def keyword(self) -> Token:
        return self._keyword

    @property
    def file(self) -> Token:
        return self._file

    @property
    def modifiers(self) -> FrozenSet[Token]:
        return self._modifiers

    def add_import(self, import_: ImportDeclaration) -> None:
        self._imports.append(import_)


class InstructionArgument:
    def __init__(self, value: Token, type_name: Optional[Type]) -> None:
        self._value = value
        self._type = type_name

    @property
    def value(self) -> Token:
        return self._value

    @property
    def type(self) -> Optional[Type]:
        return self._type


class Instruction:
    def __init__(self, name: Token, arguments: Iterable[InstructionArgument]) -> None:
        self._name = name
        self._arguments = tuple(arguments)

    @property
    def name(self) -> Token:
        return self._name

    @property
    def arguments(self) -> Tuple[InstructionArgument]:
        return self._arguments


class FunctionDefinition(FunctionDeclaration):
    def __init__(self, keyword: Token, name: Token, parameters: Iterable[Parameter], return_type_name: Type, modifiers: Iterable[Token]) -> None:
        super().__init__(keyword, name, parameters, return_type_name)
        self._modifiers = frozenset(modifiers)
        self._body: List[Instruction] = []
        self._locals: List[VariableDeclaration] = []

    @property
    def modifiers(self) -> FrozenSet[Token]:
        return self._modifiers

    @property
    def body(self) -> List[Instruction]:
        return self._body

    @property
    def locals(self) -> List[VariableDeclaration]:
        return self._locals

    def add_instruction(self, item: Instruction) -> None:
        assert_type(item, Instruction)
        self._body.append(item)

    def add_local(self, item: VariableDeclaration) -> None:
        assert_type(item, VariableDeclaration)
        self._locals.append(item)


class TypeDefinition(TypeDeclaration):
    def __init__(self, keyword: Token, name: Token, modifiers: Iterable[Token]):
        super().__init__(keyword, name)
        self._modifiers = frozenset(modifiers)
        self._fields: List[VariableDeclaration] = []
        self._functions: List[FunctionDefinition] = []

    @property
    def modifiers(self) -> FrozenSet[Token]:
        return self._modifiers

    @property
    def fields(self) -> List[VariableDeclaration]:
        return self._fields

    @property
    def functions(self) -> List[FunctionDefinition]:
        return self._functions

    def add_field(self, item: VariableDeclaration) -> None:
        assert_type(item, VariableDeclaration)
        self._fields.append(item)

    def add_function(self, item: FunctionDefinition) -> None:
        assert_type(item, FunctionDefinition)
        self._functions.append(item)


class VariableDefinition(VariableDeclaration):
    def __init__(self, keyword: Token, name: Token, type_name: Type, modifiers: Iterable[Token], value: Token) -> None:
        super().__init__(keyword, name, type_name)
        self._modifiers = frozenset(modifiers)
        self._value = value

    @property
    def modifiers(self) -> FrozenSet[Token]:
        return self._modifiers

    @property
    def value(self) -> Token:
        return self._value


class Document:
    def __init__(self) -> None:
        self._imports: List[ImportStatement] = []
        self._functions: List[FunctionDefinition] = []
        self._globals: List[VariableDeclaration] = []
        self._types: List[TypeDefinition] = []

    @property
    def imports(self) -> List[ImportStatement]:
        return self._imports

    @property
    def functions(self) -> List[FunctionDefinition]:
        return self._functions

    @property
    def globals(self) -> List[VariableDeclaration]:
        return self._globals

    @property
    def types(self):
        return self._types

    def add_import(self, item: ImportStatement) -> None:
        assert_type(item, ImportStatement)
        self._imports.append(item)

    def add_function(self, item: FunctionDefinition) -> None:
        assert_type(item, FunctionDefinition)
        self._functions.append(item)

    def add_global(self, item: VariableDeclaration) -> None:
        assert_type(item, VariableDeclaration)
        self._globals.append(item)

    def add_type(self, item: TypeDefinition) -> None:
        assert_type(item, TypeDefinition)
        self._types.append(item)
