from functools import wraps
from typing import Iterable, Callable, Dict, Union

from qasm.parsing.iparser import IParser
from qasm.parsing.itokenizer import ITokenizer, TokenizerOptions
from qasm.parsing.nodes import Node,\
    InstructionNode, DirectiveNode, FunctionDefinitionNode,\
    SectionNode, LabelNode, VariableDefinitionNode, ParameterNode, \
    TypeDefinitionNode
from qasm.parsing.asm_token import Token, TokenType
from qasm.asm import bin_types as bt


DirectiveHandler = Callable[[IParser, str], DirectiveNode]
InstructionHandler = Callable[[IParser, str], InstructionNode]


def bin_type_from_token_type(typ: TokenType):
    if typ == TokenType.Literal_Char:
        return bt.Int8
    if typ == TokenType.Literal_Int:
        return bt.Int
    if typ == TokenType.Literal_Float:
        return bt.Float
    if typ == TokenType.Literal_String:
        return bt.String
    if typ == TokenType.Literal_Bool:
        return bt.Bool
    if typ == TokenType.Literal_Bytes:
        return bt.Bytes
    if typ == TokenType.Identifier:
        return bt.RelativePointer
    raise ValueError(f"Invalid token type for literal: {typ}")


def assert_token_type(token: Token, typ: TokenType):
    if token != typ:
        raise ValueError(f"Expected \'{typ.name}\', got \"{token.value}\" at line {token.line}, char {token.char}")


class UnknownDirectiveError(Exception):
    ...


class Parser(IParser):

    def __init__(self, tokenizer: ITokenizer):
        self._tokenizer = tokenizer
        self._directives: Dict[str, DirectiveHandler] = {}
        self._default_directive_handler: DirectiveHandler = ...
        self._instructions: Dict[str, InstructionHandler] = {}

    @property
    def tokenizer(self):
        return self._tokenizer

    @property
    def default_directive_handler(self):
        return self._default_directive_handler

    @default_directive_handler.setter
    def default_directive_handler(self, value: DirectiveHandler):
        if value is not None and not callable(value):
            raise TypeError(f"default_directive_handler must be either a {DirectiveHandler} or {None}")
        self._default_directive_handler = value

    def set_directive_handler(self, directive: str, handler: Union[DirectiveHandler, None]):
        if handler is None:
            del self._directives[directive]
        else:
            if not callable(handler):
                raise TypeError(f"directive handler must be callable")
            self._directives[directive] = handler

    def set_instruction_handler(self, instruction: str, handler: Union[InstructionHandler, None]):
        if handler is None:
            del self._instructions[instruction]
        else:
            if not callable(handler):
                raise TypeError(f"instruction handler must be callable")
            self._instructions[instruction] = handler

    def directive_handler(self, directive: str):
        def decorator(func):
            self.set_directive_handler(directive, func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def instruction_handler(self, directive: str):
        def decorator(func):
            self.set_instruction_handler(directive, func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def parse(self, **_) -> Iterable[Node]:
        nodes = []

        self.tokenizer.advance()

        while self._tokenizer.has_tokens:
            token = self._tokenizer.token

            if token == TokenType.Comment:
                # ignore comments
                self._tokenizer.advance()
                continue

            if token == TokenType.WhiteSpace:
                # ignore white space
                self._tokenizer.advance()
                continue

            if token == TokenType.NewLine:
                # ignore new lines
                self._tokenizer.advance()
                continue

            node = None

            if token == TokenType.Dot:
                try:
                    self._tokenizer.eat(token.value)
                    directive_name = self.get_token(TokenType.Identifier).value
                    node = self._directives[directive_name](self, directive_name)
                except KeyError:
                    if not callable(self._default_directive_handler):
                        raise UnknownDirectiveError(f"Could not handle directive \"{token.value}\" at line {token.line}, char {token.char}")
                    node = self._default_directive_handler(self, token.value)

            elif token == TokenType.Identifier:
                try:
                    node = self._instructions[token.value](self, token.value)
                except KeyError:
                    node = self._parse_instruction(token.value)

            if node is not None:
                nodes.append(node)

        return nodes

    def get_token(self, typ: TokenType):
        token = self._tokenizer.token
        assert_token_type(token, typ)
        self._tokenizer.eat(typ)
        return token

    def _parse_instruction(self, opname: str) -> InstructionNode:
        self._tokenizer[TokenizerOptions.EmitNewLine] = True

        self._tokenizer.eat(opname)

        args = []
        while self.tokenizer.token != TokenType.NewLine and self.tokenizer.token != TokenType.EOF:
            token = self._tokenizer.token
            if token == TokenType.Comma:
                self.tokenizer.advance()
                token = self.tokenizer.token

            if token.type.is_literal():
                if token.type == TokenType.Literal_Hex:
                    token = Token(token.line, token.char, TokenType.Literal_Int, str(int(token.value, base=16)))
                arg = InstructionNode.InstructionArgument(token)
            elif token == TokenType.Identifier:
                typename = token
                self.tokenizer.eat(typename.value)
                token = self._tokenizer.token
                if token == TokenType.NewLine:
                    args.append(InstructionNode.InstructionArgument(typename))
                    break
                elif token == TokenType.Comma:
                    arg = InstructionNode.InstructionArgument(typename)
                elif token == TokenType.Dot:
                    self.get_token(TokenType.Dot)
                    assert_token_type(self._tokenizer.token, TokenType.Identifier)
                    member_name = self._tokenizer.token
                    arg = InstructionNode.InstructionArgument(member_name, typename.value)
                else:
                    if token != TokenType.Identifier and not token.type.is_literal():
                        raise ValueError(f"Typed instruction argument must be an identifier or a value")
                    if token.type == TokenType.Literal_Hex:
                        token = Token(token.line, token.char, TokenType.Literal_Int, str(int(token.value, base=16)))
                    arg = InstructionNode.InstructionArgument(token, typename.value)
                    self.tokenizer.advance()
                    token = self._tokenizer.token
                    if token == TokenType.NewLine:
                        args.append(arg)
                        break
            elif token == TokenType.LeftCurlyBracket:
                self.tokenizer.eat(token.value)
                data = []
                line, char = token.line, token.char
                while self.tokenizer.token != TokenType.RightCurlyBracket:
                    data.append(int(self.get_token(TokenType.Literal_Int).value))
                    if self.tokenizer.token != TokenType.RightCurlyBracket:
                        self.get_token(TokenType.Comma)
                arg = InstructionNode.InstructionArgument(Token(line, char, TokenType.Literal_Bytes, bytes(data).decode("ascii")))
            else:
                raise ValueError(f"Invalid token type in instruction: \'{token.type.name}\' at line {token.line}, char {token.char}")
            args.append(arg)
            self.tokenizer.advance()

        self._tokenizer[TokenizerOptions.EmitNewLine] = False

        return InstructionNode(opname, args)


def default_parser(tokenizer: ITokenizer):
    parser = Parser(tokenizer)
    parser.set_directive_handler(SectionNode.directive_name(), _section_handler)
    parser.set_directive_handler(FunctionDefinitionNode.directive_name(), _function_handler)
    parser.set_directive_handler(LabelNode.directive_name(), _label_handler)
    parser.set_directive_handler(VariableDefinitionNode.directive_name(), _var_handler)
    parser.set_directive_handler(TypeDefinitionNode.directive_name(), _type_handler)
    return parser


def parse(tokenizer: ITokenizer, **options):
    parser = Parser(tokenizer)
    return parser.parse(**options)


def _section_handler(p: IParser, s: str):
    name = p.get_token(TokenType.Identifier).value
    return SectionNode(name)


def _function_handler(p: IParser, s: str):
    typename = p.get_token(TokenType.Identifier).value
    name = p.get_token(TokenType.Identifier).value
    p.get_token(TokenType.LeftCurvyBracket)
    params = []
    if p.tokenizer.token == TokenType.Identifier:
        typ = p.get_token(TokenType.Identifier).value
        if p.tokenizer.token == TokenType.Identifier:
            param_name = p.get_token(TokenType.Identifier).value
        else:
            param_name = str(len(params))
        params.append(ParameterNode(param_name, typ))
        while p.tokenizer.token != TokenType.RightCurvyBracket:
            p.get_token(TokenType.Comma)
            typ = p.get_token(TokenType.Identifier).value
            if p.tokenizer.token == TokenType.Identifier:
                param_name = p.get_token(TokenType.Identifier).value
            else:
                param_name = str(len(params))
            params.append(ParameterNode(param_name, typ))
    p.get_token(TokenType.RightCurvyBracket)
    modifiers = set()
    while p.tokenizer.token != TokenType.Colon:
        modifiers.add(p.get_token(TokenType.Identifier).value)
    p.get_token(TokenType.Colon)
    return FunctionDefinitionNode(name, typename, params, modifiers)


def _var_handler(p: IParser, s: str):
    typename = p.get_token(TokenType.Identifier).value
    if p.tokenizer.token == TokenType.Identifier:
        name = p.get_token(TokenType.Identifier).value
    else:
        name = None
    return VariableDefinitionNode(typename, name)


def _label_handler(p: IParser, s: str):
    name = p.get_token(TokenType.Identifier).value
    return LabelNode(name)


def _type_handler(p: IParser, s: str):
    name = p.get_token(TokenType.Identifier).value
    modifiers = []
    while p.tokenizer.token != TokenType.Colon:
        modifiers.append(p.get_token(TokenType.Identifier).value)
    p.get_token(TokenType.Colon)
    return TypeDefinitionNode(name, modifiers)


if __name__ == '__main__':
    from qasm.parsing.tokenizer import Tokenizer
    with open("../../tests/test1.qsm") as src:
        tokenizer = Tokenizer(src.read())
        parser = Parser(tokenizer)
        parser.set_directive_handler("section", _section_handler)
        parser.set_directive_handler("func", _function_handler)
        for item in parser.parse():
            print(item)
