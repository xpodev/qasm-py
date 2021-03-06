from typing import Union, List, Optional

try:
    from .iparser import *
    from .document import *
    from .itokenizer import *
except ImportError:
    from qasm.parsing.iparser import *
    from qasm.parsing.document import *
    from qasm.parsing.itokenizer import *


class Parser(IParser):
    @staticmethod
    def _get_token(tokenizer: ITokenizer, value: Union[str, TokenType]) -> Token:
        token = tokenizer.token
        tokenizer.eat(value)
        return token

    def _try_get_token(self, tokenizer: ITokenizer, value: Union[str, TokenType]) -> Optional[Token]:
        if tokenizer.token == value:
            return self._get_token(tokenizer, value)
        return None

    def _try_get_type(self, tokenizer: ITokenizer) -> Optional[Type]:
        if tokenizer.token == TokenType.Identifier:
            return self._get_type(tokenizer)
        return None

    def _get_type(self, tokenizer: ITokenizer) -> Type:
        type_name = self._get_token(tokenizer, TokenType.Identifier)
        typ = Type(type_name)
        while tokenizer.token == TokenType.Asterisk:
            typ = Pointer(typ, self._get_token(tokenizer, TokenType.Asterisk))
        return typ

    def _get_parameter(self, tokenizer: ITokenizer) -> Parameter:
        typ = self._get_type(tokenizer)
        name = self._try_get_token(tokenizer, TokenType.Identifier)
        return Parameter(name, typ)

    def _get_parameters(self, tokenizer: ITokenizer) -> List[Parameter]:
        try:
            params = [self._get_parameter(tokenizer)]
        except UnexpectedTokenError:
            return []
        while self._try_get_token(tokenizer, TokenType.Comma):
            params.append(self._get_parameter(tokenizer))
        return params

    def _get_modifiers(self, tokenizer: ITokenizer) -> List[Token]:
        modifiers = []
        while True:
            modifier = self._try_get_token(tokenizer, TokenType.Identifier)
            if not modifier:
                break
            modifiers.append(modifier)
        return modifiers

    def _get_import_declaration(self, tokenizer: ITokenizer) -> ImportDeclaration:
        import_type = self._get_token(tokenizer, TokenType.Identifier)
        name = self._get_fully_qualified_name(tokenizer)
        return ImportDeclaration(import_type, name, {
            VariableDeclaration.declaration_keyword: ImportType.Variable,
            FunctionDeclaration.declaration_keyword: ImportType.Function,
            TypeDeclaration.declaration_keyword: ImportType.Type
        }[import_type.value])

    def _get_import_statement(self, tokenizer: ITokenizer) -> ImportStatement:
        keyword = self._get_token(tokenizer, ImportStatement.declaration_keyword)
        modifiers = self._get_modifiers(tokenizer)
        source = self._get_token(tokenizer, TokenType.Literal_String)
        import_statement = ImportStatement(keyword, source, modifiers)
        if not self._try_get_token(tokenizer, TokenType.SemiColon):
            tokenizer.eat(TokenType.LeftCurlyBracket)
            while not self._try_get_token(tokenizer, TokenType.RightCurlyBracket):
                import_statement.add_import(self._get_import_declaration(tokenizer))
        return import_statement

    def _get_instruction(self, tokenizer: ITokenizer) -> Instruction:
        name = self._get_fully_qualified_name(tokenizer)
        arguments = self._get_instruction_arguments(tokenizer)
        return Instruction(name, arguments)

    def _get_instruction_argument(self, tokenizer: ITokenizer) -> InstructionArgument:
        value = self._get_fully_qualified_name(tokenizer) if tokenizer.token == TokenType.Identifier else self._get_literal(tokenizer)
        if self._try_get_token(tokenizer, TokenType.Colon):
            typ = self._get_type(tokenizer)
        else:
            typ = None
        return InstructionArgument(value, typ)

    def _get_instruction_arguments(self, tokenizer: ITokenizer) -> List[InstructionArgument]:
        try:
            arguments = [self._get_instruction_argument(tokenizer)]
        except UnexpectedTokenError:
            return []
        while self._try_get_token(tokenizer, TokenType.Comma):
            arguments.append(self._get_instruction_argument(tokenizer))
        return arguments

    def _get_function_signature(self, tokenizer: ITokenizer) -> FunctionDeclaration:
        keyword = self._get_token(tokenizer, FunctionDeclaration.declaration_keyword)
        name = self._get_fully_qualified_name(tokenizer)
        self._get_token(tokenizer, TokenType.LeftCurvyBracket)
        params = self._get_parameters(tokenizer)
        tokenizer.eat(TokenType.RightCurvyBracket)
        tokenizer.eat(TokenType.Colon)
        return_type = self._get_type(tokenizer)
        return FunctionDeclaration(keyword, name, params, return_type)

    def _get_function_definition(self, tokenizer: ITokenizer) -> FunctionDefinition:
        declaration = self._get_function_signature(tokenizer)
        if self[ParserOptions.AllowFunctionModifiers]:
            modifiers = self._get_modifiers(tokenizer)
        else:
            modifiers = []
        func = FunctionDefinition(declaration.keyword, declaration.name, declaration.parameters, declaration.return_type_name, modifiers)
        tokenizer.eat(TokenType.LeftCurlyBracket)
        while not self._try_get_token(tokenizer, TokenType.RightCurlyBracket):
            if tokenizer.token == VariableDeclaration.declaration_keyword:
                func.add_local(self._get_variable_declaration(tokenizer))
            else:
                func.add_instruction(self._get_instruction(tokenizer))
        return func

    def _get_fully_qualified_name(self, tokenizer: ITokenizer) -> FullyQualifiedName:
        parts = [self._get_token(tokenizer, TokenType.Identifier)]
        while self._try_get_token(tokenizer, TokenType.Dot):
            parts.append(self._get_token(tokenizer, TokenType.Identifier))
        return FullyQualifiedName(*parts)

    def _get_literal(self, tokenizer: ITokenizer) -> Token:
        if not tokenizer.token.type.is_literal():
            raise UnexpectedTokenError(TokenType.Literal, tokenizer.token)
        return self._get_token(tokenizer, tokenizer.token.type)

    def _get_variable_declaration(self, tokenizer: ITokenizer) -> VariableDeclaration:
        keyword = self._get_token(tokenizer, VariableDeclaration.declaration_keyword)
        name = self._get_fully_qualified_name(tokenizer)
        tokenizer.eat(TokenType.Colon)
        typ = self._get_type(tokenizer)
        if self._try_get_token(tokenizer, TokenType.SemiColon):
            return VariableDeclaration(keyword, name, typ)
        if self[ParserOptions.AllowVariableModifiers]:
            modifiers = self._get_modifiers(tokenizer)
        else:
            modifiers = []
        tokenizer.eat(TokenType.Equal)
        value = self._get_literal(tokenizer)
        tokenizer.eat(TokenType.SemiColon)
        return VariableDefinition(keyword, name, typ, modifiers, value)

    def _get_type_definition(self, tokenizer: ITokenizer) -> TypeDefinition:
        keyword = self._get_token(tokenizer, TypeDefinition.declaration_keyword)
        name = self._get_fully_qualified_name(tokenizer)
        modifiers = self._get_modifiers(tokenizer)
        typ = TypeDefinition(keyword, name, modifiers)
        tokenizer.eat(TokenType.LeftCurlyBracket)
        while not self._try_get_token(tokenizer, TokenType.RightCurlyBracket):
            if tokenizer.token == VariableDeclaration.declaration_keyword:
                typ.add_field(self._get_variable_declaration(tokenizer))
            elif tokenizer.token == FunctionDefinition.declaration_keyword:
                typ.add_function(self._get_function_definition(tokenizer))
            else:
                raise UnexpectedTokenError(" or ".join(
                    [
                        VariableDeclaration.declaration_keyword,
                        FunctionDefinition.declaration_keyword
                    ]
                ), tokenizer.token)
        return typ

    def parse(self, tokenizer: ITokenizer) -> Document:
        document = Document()
        tokenizer[TokenizerOptions.EmitComments] = False
        tokenizer.advance()
        with self.options(ParserOptions.AllowFunctionModifiers, ParserOptions.AllowVariableModifiers).enabled():
            while tokenizer.has_tokens:
                token = tokenizer.token
                if token == FunctionDefinition.declaration_keyword:
                    document.add_function(self._get_function_definition(tokenizer))
                elif token == VariableDefinition.declaration_keyword:
                    document.add_global(self._get_variable_declaration(tokenizer))
                elif token == TypeDefinition.declaration_keyword:
                    document.add_type(self._get_type_definition(tokenizer))
                elif token == ImportStatement.declaration_keyword:
                    document.add_import(self._get_import_statement(tokenizer))
                else:
                    raise UnexpectedTokenError(" or ".join(
                        [
                            VariableDefinition.declaration_keyword,
                            FunctionDefinition.declaration_keyword,
                            TypeDefinition.declaration_keyword,
                            ImportStatement.declaration_keyword
                        ]
                    ), token)

        return document


if __name__ == '__main__':
    from qasm.parsing.tokenizer import Tokenizer
    with open("../../tests/hello_world.qsm") as src:
        tokenizer = Tokenizer(src.read())
        parser = Parser()
        document = parser.parse(tokenizer)

        WIDTH = 50
        CHAR = '-'

        print(" IMPORTS ".center(WIDTH, CHAR))
        print()

        for imp in document.imports:
            print(f"import [{' '.join(map(lambda x: x.value, imp.modifiers))}] {imp.file.value} at line {imp.keyword.line} {{")
            for item in imp.imports:
                print(f"\t{item.import_type.name} {item.name.name.value}")
            print("}")
            print()
        print()

        print(" TYPES ".center(WIDTH, CHAR))
        print()

        for typ in document.types:
            print(f"type {typ.name}{' ' + ' '.join(map(str, typ.modifiers))} declared at line {typ.keyword.line} {{")
            for field in typ.fields:
                print(f"\tfield {field.name}: {field.type}")
            print()
            for func in typ.functions:
                print(f"\tmethod {func.name}({', '.join(map(lambda p: f'{p.name}: {p.type}', func.parameters))}) [{' '.join(map(lambda x: x.value, func.modifiers))}] declared at line {func.keyword.line} {{")
                for instruction in func.body:
                    print(f"\t\t{instruction.name}", ", ".join(map(lambda x: f"{x.value}{f': {x.type}' if x.type else ''}", instruction.arguments)))
                print("\t}")
            print("}")
            print()
        print()

        print(" GLOBALS ".center(WIDTH, CHAR))
        print()

        for var in document.globals:
            print(f"global {var.name}: {var.type}{f' = {var.value.value}' if isinstance(var, VariableDefinition) else ''}")
            print()
        print()

        print(" FUNCTIONS ".center(WIDTH, CHAR))
        print()
        for func in document.functions:
            print(f"function {func.name}({', '.join(map(lambda p: f'{p.name.value}: {p.type}', func.parameters))}) [{' '.join(map(lambda x: x.value, func.modifiers))}] declared at line {func.keyword.line} {{")
            for instruction in func.body:
                print(f"\t{instruction.name}", ", ".join(map(lambda x: f"{x.value}{f': {x.type}' if x.type else ''}", instruction.arguments)))
            print('}')
            print()
