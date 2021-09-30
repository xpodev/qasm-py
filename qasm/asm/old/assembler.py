from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Iterable, Dict, Union, List, Set, Collection

from qasm.asm.old.bin_types import *
from qasm.asm.old.function import *
from qasm.asm.old.instruction import *
from qasm.asm.old.instructions import *
from qasm.asm.old.label import *
from qasm.asm.old.type import TypeDefinition
from qasm.parsing.old.nodes import Node, SectionNode, InstructionNode, LabelNode, FunctionDefinitionNode, VariableDefinitionNode, TypeDefinitionNode
from qasm.parsing.old.parser import default_parser, bin_type_from_token_type
from qasm.parsing.tokenizer import Tokenizer, Token, TokenType
from qasm.qpl.exports import ExportTable
from qasm.qpl.file import QPLFile, QPLFlags, read_file


class UnknownInstructionError(Exception):
    ...


class LabelManager:
    def __init__(self):
        self._labels: Dict[str, Label] = {}

    @property
    def labels(self):
        return tuple(self._labels.values())

    @property
    def label_names(self):
        return tuple(self._labels.keys())

    def insert_label(self, name: str, offset: int) -> Label:
        return self.add_label(Label(name, offset))

    def get_label(self, name: str) -> Label:
        return self._labels[name]

    def add_label(self, label: Label):
        if label.name in self._labels:
            raise KeyError(f"Label already exists")
        self._labels[label.name] = label
        return label

    def recalculate_labels(self, offset: int):
        for label in self._labels.values():
            label.offset += offset


class AssemblySectionMeta(ABCMeta):
    def __init__(cls, name, bases, ns):
        super().__init__(name, bases, ns)
        if not bases:
            cls._name = name
        else:
            cls._name = cls._name

    @property
    def name(cls):
        return cls._name

    def __getitem__(cls, item):
        cls._name = item
        return cls


class AssemblySection(metaclass=AssemblySectionMeta):
    @property
    def name(self):
        return self._name

    @abstractmethod
    def on_instruction(self, instruction: InstructionNode, assembler):
        ...

    @abstractmethod
    def to_bytes(self, assembler) -> bytes:
        ...


class ConfigSection(AssemblySection["config"]):
    class Option:
        def __init__(self, name: str, *typ: TypeMeta, initial_value=None):
            self._name = name
            self._types = typ
            self._value = initial_value if initial_value else tuple(map(lambda x: x.default(), self._types))

        @property
        def name(self):
            return self._name

        @property
        def types(self):
            return self._types

        @property
        def value(self):
            return self._value

        @value.setter
        def value(self, value):
            self._value = value

        def __str__(self):
            return f"{self._name} :: {', '.join(map(str, self._types))}"

    def __init__(self, *config: Option, allow_custom_options: bool = False):
        self._config: Dict[str, Collection[TypeMeta]] = {opt.name: opt.types for opt in config}
        self._config_values: Dict[str, ConfigSection.Option] = {}
        self._custom: Dict[str, ConfigSection.Option] = {} if allow_custom_options else None

    def on_instruction(self, instruction: InstructionNode, assembler):
        opt_name = instruction.opname
        option = self.get_option(opt_name)
        if option is None:
            raise ValueError(f"No option {opt_name} was found")
        elif len(instruction.arguments) != len(option.types):
            raise ValueError(f"Option takes exactly {len(option.types)} arguments but {len(instruction.arguments)} were given")
        values = []
        for arg, param in zip(instruction.arguments, option.types):
            values.append(arg.value.value)
        option.value = values

    def add_option(self, option: Option):
        if option.name in self._config:
            raise KeyError(f"Option {option} with the same name already exists as {self._config[option.name]}")
        self._config[option.name] = option

    def get_option(self, name: str):
        try:
            types = self._config[name]
            if name not in self._config_values:
                self._config_values[name] = ConfigSection.Option(name, *types)
            return self._config_values[name]
        except KeyError:
            if self._custom is not None:
                option = self._custom[name] = ConfigSection.Option(name)
                return option
            return None

    def set_option(self, name: str, value):
        self.get_option(name).value = value

    def to_bytes(self, assembler) -> bytes:
        # return b"".join(
        #     [
        #         (
        #             struct.pack(f"{len(option.name) + 1}s", option.name.encode("ascii")) +
        #             b"".join([
        #                 struct.pack(
        #                     f"b {typ.size()}b",
        #                     TYPE_INDEX[typ.name()],
        #                     *typ.to_bytes(typ.parse(value)) if typ is not Pointer else typ.to_bytes(assembler.label_manager.get_label(value).offset)
        #                 )
        #                 for typ, value in zip(option.types, option.value)
        #             ])
        #         )
        #         for option in self._config.values()
        #     ]
        # )
        return b"".join([
            b"".join([
                typ.to_bytes(typ.parse(value) if not issubclass(typ, Pointer) else assembler.label_manager.get_label(value).offset)
                for value, typ in zip(option.value, option.types)
            ])
            for option in self._config_values.values()
        ])

    def __getitem__(self, item):
        return self.get_option(item)

    def __contains__(self, item):
        return item in self._config or ((item in self._custom) if self._custom else False)


class SizedSection(AssemblySection):
    def __init__(self):
        self._labels: List[Label] = []

    @property
    @abstractmethod
    def size(self) -> int:
        ...

    def add_label(self, label: Label):
        self._labels.append(label)

    def recalculate_labels(self, offset: int):
        for label in self._labels:
            label.offset += offset


class CodeSection(SizedSection["code"]):
    def __init__(self):
        super().__init__()
        self._instructions: List[Instruction] = []
        self._size = 0

    @property
    def size(self):
        return self._size

    def on_instruction(self, instruction: InstructionNode, assembler):
        try:
            inst = INSTRUCTIONS[instruction.opname]
            if len(instruction.arguments) != len(inst.types):
                raise ValueError(f"Instruction \"{inst.name}\" takes {len(inst.types)} arguments, but {len(instruction.arguments)} were given")
        except KeyError:
            raise UnknownInstructionError(f"Unknown instruction: \"{instruction.opname}\"") from None
        else:
            types_ = []
            args = []
            for pt, arg in zip(inst.types, instruction.arguments):
                if pt is Type:
                    pt = Int8
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, TYPE_INDEX[arg.value.value])
                    arg = InstructionNode.InstructionArgument(tkn, pt.name)
                elif pt is TypeSize:
                    pt = Int
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, assembler.get_type(arg.value.value).size)
                    arg = InstructionNode.InstructionArgument(tkn, pt.name)
                if isinstance(pt, AnyOf):
                    if arg.type is None:
                        raise ValueError(f"One of {tuple(map(str, pt.types))} must be supplied (error at line {arg.value.line}, char {arg.value.char})")
                    pt = TYPE_TABLE[arg.type]
                    types_.append(Int8)
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, TYPE_INDEX[pt.name])
                    args.append(InstructionNode.InstructionArgument(tkn))
                if pt is Variable:
                    pt = assembler.get_type(arg.type) if arg.type else bin_type_from_token_type(arg.value.type)
                    if isinstance(pt, TypeDefinition):
                        pt = Pointer[pt]
                    types_.append(Int8)
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, TYPE_INDEX[pt.name])
                    args.append(InstructionNode.InstructionArgument(tkn))
                if pt is Local:
                    name = arg.value.value
                    local = assembler.current_function.locals[name]
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, assembler.get_type(local.type.name).index())
                    args.append(InstructionNode.InstructionArgument(tkn))
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, local.index)
                    args.append(InstructionNode.InstructionArgument(tkn))
                    types_.append(Int8)
                    types_.append(Local)
                    continue
                elif pt is Argument:
                    name = arg.value.value
                    param = assembler.current_function.parameters[name]
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, assembler.get_type(param.type.name).index())
                    args.append(InstructionNode.InstructionArgument(tkn))
                    tkn = Token(arg.value.line, arg.value.char, TokenType.Literal_Int, param.index)
                    args.append(InstructionNode.InstructionArgument(tkn))
                    types_.append(Int8)
                    types_.append(Argument)
                    continue
                args.append(arg)
                types_.append(pt)

            built_instruction = InstructionDefinition(inst.name, inst.code, *types_)
            size = built_instruction.get_size()

            if instruction.opname == "call":
                # size adds 2 more bytes (num_params, num_locals) at compile time
                # i.e. when generating the bytes
                size += 2

            res = Instruction(built_instruction, args, self._size)
            self._size += size
            self._instructions.append(res)
            return res

    def recalculate_labels(self, offset: int):
        super().recalculate_labels(offset)
        for instruction in self._instructions:
            instruction.offset += offset

    def to_bytes(self, assembler):
        data = []
        for instruction in self._instructions:
            inst = instruction.instruction
            types_ = []
            args = []
            for pt, arg in zip(inst.types, instruction.arguments):
                if issubclass(pt, Pointer) or pt is Local or pt is Argument:
                    name = arg.value.value
                    try:
                        local = assembler.current_function.locals[name]
                        args.append(TYPE_INDEX[local.type.name])
                        args.append(local.index)
                        types_.append(Int8)
                        types_.append(Local)
                        continue
                    except KeyError:
                        ...
                    try:
                        param = assembler.current_function.parameters[name]
                        args.append(TYPE_INDEX[param.type.name])
                        args.append(param.index)
                        types_.append(Int8)
                        types_.append(InstructionArgument)
                        continue
                    except KeyError:
                        ...
                    try:
                        if issubclass(pt, Pointer) and isinstance(pt.type(), TypeDefinition):
                            arg = pt.type().get_field(name).offset
                            pt = Int
                        else:
                            typ = assembler.label_manager.get_label(name)
                            arg = typ.offset
                    except KeyError:
                        arg = int(arg.value.value)
                    if pt is RelativePointer:
                        arg -= instruction.offset
                else:
                    arg = pt.parse(arg.value.value)
                types_.append(pt)
                args.append(arg)
            if instruction.opname == "call":
                func = assembler.label_manager.get_label(instruction.arguments[0].value.value)
                if not isinstance(func, FunctionReference):
                    raise TypeError(f"Can't call a non-function object: {instruction.arguments[0]}")
                types_.append(Int8)
                types_.append(Int8)
                args.append(func.num_params)
                args.append(func.num_locals)
            data.extend(inst.to_bytes(types_, *args))
        return data


class DataSection(SizedSection["data"]):
    def __init__(self):
        super().__init__()
        self._data = bytearray()

    @property
    def size(self) -> int:
        return len(self._data)

    def on_instruction(self, instruction: InstructionNode, assembler):
        if instruction.opname != "db":
            raise ValueError(f"Invalid instruction in data section: {instruction.opname}")
        for arg in instruction.arguments:
            typ = bin_type_from_token_type(arg.value.type) if arg.type is None else TYPE_TABLE[arg.type]
            self._data.extend(typ.to_bytes(typ.parse(arg.value.value)))

    def to_bytes(self, assembler) -> bytes:
        return bytes(self._data)


class ExportSection(AssemblySection["exports"]):
    def __init__(self):
        self._exports = ExportTable()

    def on_instruction(self, instruction: InstructionNode, assembler):
        raise Exception(F"Can't manually export a function")

    def add_export(self, func: Function):
        self._exports.add_export(func)

    def to_bytes(self, assembler) -> bytes:
        return self._exports.to_bytes()


class ImportSection(SizedSection["imports"]):
    def __init__(self):
        super().__init__()
        self._data: bytearray = bytearray()
        self._current_export_table: Union[ExportTable, None] = None
        self._all_imports: Set[str] = set()

    @property
    def size(self) -> int:
        return len(self._data)

    def on_instruction(self, instruction: InstructionNode, assembler):
        if instruction.opname == "load":
            path = instruction.arguments[0].value.value
            file = read_file(path)
            self._current_export_table = ExportTable.from_bytes(file.sections[ExportSection.name])
            self._data.extend(file.raw_data)
        elif instruction.opname == "import":
            if self._current_export_table is None:
                raise ValueError(f"Can't import function without loading a file first. use \'load {{file_path}}\' before importing.")
            func_name = instruction.arguments[0].value.value
            try:
                import_name = instruction.arguments[1].value.value
            except IndexError:
                import_name = func_name
            if func_name in self._all_imports:
                raise ValueError(f"Function \"{func_name}\" was already imported. Try importing it with another name.")
            func = self._current_export_table.get_export(func_name)
            f_reference = FunctionReference(import_name, func.offset, func.return_type, func.parameter_types, func.num_locals)
            print(f"Importing function: {func_name} as {import_name} at {f_reference.offset} with {func.num_locals} locals")
            assembler.add_label(f_reference)

    def to_bytes(self, assembler) -> bytes:
        return bytes(self._data)


class TypesSection(SizedSection["types"]):
    def __init__(self):
        super().__init__()
        self._types: Dict[str, TypeDefinition] = {}
        self._current_type: Union[TypeDefinition, None] = None
        self._size = 0

    @property
    def size(self) -> int:
        return self._size

    def add_type(self, typ: TypeDefinition):
        if not isinstance(typ, TypeDefinition):
            raise TypeError(f"Can't add non-type item to section \"{self.name}\"")
        if typ.name in self._types:
            raise ValueError(f"Type {typ.name} already exists")
        self._current_type = self._types[typ.name] = typ
        self.add_label(typ)

    def get_type(self, name: str):
        return self._types[name]

    def on_instruction(self, instruction: InstructionNode, assembler):
        if instruction.opname == "field":
            field_info, *_ = instruction.arguments
            type_name, field_name = field_info.type, field_info.value.value
            self._add_field(field_name, assembler.get_type(type_name))
        else:
            raise UnknownInstructionError(f"Unknown instruction in section \"{self.name}\": {instruction.opname}")

    def _add_field(self, name: str, typ: TypeMeta):
        if self._current_type is None:
            raise ValueError(f"Can't define a field outside a type definition")
        self._size += self._current_type.add_field(name, typ).type.size

    def to_bytes(self, assembler) -> bytes:
        return b"\xCA" * self._size


class Assembler:
    def __init__(self):
        self._config = ConfigSection(
            ConfigSection.Option("entry", Pointer)
        )
        self._code = CodeSection()
        self._data = DataSection()
        self._exports = ExportSection()
        self._imports = ImportSection()
        self._types = TypesSection()

        self._sections_ordered = [
            self._config,
            self._types,
            self._data,
            self._code,
            self._imports,
            self._exports
        ]

        self._sections = {
            section.name: section for section in self._sections_ordered
        }

        self._current_section: Union[AssemblySection, None] = None
        self._current_function: Union[Function, None] = None

        self._labels = LabelManager()

    @property
    def label_manager(self):
        return self._labels

    @property
    def current_function(self):
        return self._current_function

    def assemble(self, nodes: Iterable[Node]) -> QPLFile:
        file = QPLFile()

        for node in nodes:
            if isinstance(node, SectionNode):
                self._current_section = self._sections[node.name] if node.name != "$null" else None
            elif isinstance(node, InstructionNode):
                if self._current_section is not None:
                    if node.opname == "ret":
                        if self._current_function.return_type is Void:
                            res = self._current_section.on_instruction(
                                InstructionNode(
                                    "push",
                                    (
                                        InstructionNode.InstructionArgument(Token(-1, -1, TokenType.Literal_Int, "0")),
                                    )),
                                self)
                            if self._current_section == self._code:
                                self._current_function.body.append(res)
                    res = self._current_section.on_instruction(node, self)
                    if self._current_section == self._code:
                        self._current_function.body.append(res)
                else:
                    print(f"WARNING: instruction outside section ignored\n{node}")
            elif isinstance(node, VariableDefinitionNode):
                name = node.name if node.name else str(len(self._current_function.locals))
                try:
                    type_ = TYPE_TABLE[node.type]
                except KeyError:
                    type_ = Pointer[self._types.get_type(node.type)]
                self._current_function.locals[name] = Parameter(name, type_, len(self._current_function.locals))
            elif isinstance(node, FunctionDefinitionNode):
                self._current_function = Function(
                    node.name,
                    self._code.size,
                    self.get_type(node.return_type),
                    {
                        p.name: Parameter(p.name, self.get_type(p.type), i) for i, p in enumerate(node.parameters)
                    },
                    {},
                    (),
                    node.modifiers
                )
                if self._current_function.is_exported:
                    self._exports.add_export(self._current_function)
                self.add_label(self._current_function)
            elif isinstance(node, TypeDefinitionNode):
                self._types.add_type(TypeDefinition(node.name, self._types.size, node.modifiers))
            elif isinstance(node, LabelNode):
                self.create_label(node.name)

        offset = 0

        for section in self._sections_ordered:
            if isinstance(section, SizedSection):
                section.recalculate_labels(offset)
                offset += section.size
            else:
                offset += len(section.to_bytes(self))

        for section in self._sections_ordered:
            file.add_section(section.name, section.to_bytes(self))

        return file

    def get_type(self, name: str):
        try:
            return TYPE_TABLE[name]
        except KeyError:
            return self._types.get_type(name)

    def add_label(self, label: Label):
        if isinstance(self._current_section, SizedSection):
            self._current_section.add_label(self._labels.add_label(label))
        else:
            raise ValueError(f"Can't add label outside a sized section \"{self._current_section.name}\"")

    def create_label(self, name: str):
        if not isinstance(self._current_section, SizedSection):
            return TypeError(f"Labels can only be added to sections with size")
        self._current_section.add_label(self.label_manager.insert_label(name, self._current_section.size))


if __name__ == '__main__':
    src_path = "../../tests/test1.qsm"
    dst_path = Path(src_path).with_suffix(".qpl")
    with open(src_path) as src:
        tokenizer = Tokenizer(src.read())
        parser = default_parser(tokenizer)
        assembler = Assembler()
        assembler.assemble(parser.parse(), QPLFlags.HasEntryPoint | QPLFlags.HasExports).write(dst_path)
