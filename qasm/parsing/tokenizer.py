from qasm.parsing.itokenizer import ITokenizer, TokenizerOptions
from qasm.parsing.asm_token import Token
from qasm.parsing.tokens import TokenType


class Tokenizer(ITokenizer):
    class TokenizerOptionsWrapper:
        def __init__(self, tokenizer, *options: TokenizerOptions):
            self._tokenizer = tokenizer
            self._options = set(options)

        def set_options(self, *args: TokenizerOptions):
            self._options = set(args)

        def options(self, value: bool):
            for option in self._options:
                self._tokenizer[option] = value

        def __enter__(self):
            self.options(True)
            return self._tokenizer

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.options(False)
            return False

    def __init__(self, source: str):
        self._source = source
        self._token = None
        self._current = 0
        self._line = 1
        self._char = 1
        self._options = {
            key: False for key in TokenizerOptions
        }

    @property
    def token(self):
        return self._token

    @property
    def char(self):
        return self._source[self._current]

    @property
    def next_char(self):
        try:
            return self._source[self._current + 1]
        except IndexError:
            return ""

    @property
    def has_tokens(self) -> bool:
        return self._current >= 0 and self._token != TokenType.EOF

    @property
    def emit_newline(self):
        return self[TokenizerOptions.EmitNewLine]

    @emit_newline.setter
    def emit_newline(self, value: bool):
        self[TokenizerOptions.EmitNewLine] = value

    def _create_token(self, typ: TokenType, value: str) -> Token:
        self._token = Token(self._line, self._char, typ, value)
        if typ in {TokenType.Literal_Char, TokenType.Literal_String}:
            value += "00"
        self._next_string(value)
        self._current += 1
        return self._token

    def _next_char(self, c: str):
        if c == '\n':
            self._line += 1
            self._char = 1
        elif c == '\r':
            self._char = 1
        else:
            self._char += 1

    def _next_string(self, s: str):
        list(map(self._next_char, s))

    def _get_line_comment(self):
        buffer = []
        try:
            while self.char != '\n':
                buffer.append(self.char)
                self._current += 1
            if self[TokenizerOptions.IncludeCommentEOL]:
                buffer.append(self.char)
                self._current += 1
        except IndexError:
            ...
        return "".join(buffer)

    def _get_identifier(self):
        if self._is_identifier_first_character(self.char):
            buffer = []
        else:
            raise ValueError(f"Expected an identifier, got \'{self.char}\' at line {self._line}, char {self._char}")
        while self._is_identifier_character(self.char):
            buffer.append(self.char)
            self._current += 1
        if buffer:
            self._current -= 1
        return "".join(buffer)

    def _get_hex(self):
        if self.char != 'x':
            raise ValueError(f"Hex number literal must begin with an \'x\'")
        self._current += 1
        return self._get_integer16()

    def _get_integer16(self):
        buffer = []
        while '0' <= self.char <= '9' or 'a' <= self.char.lower() <= 'f':
            buffer.append(self.char)
            self._current += 1
        self._current -= 1
        return "".join(buffer)

    def _get_integer10(self):
        buffer = []
        if self.char == '-':
            buffer.append(self.char)
            self._current += 1
        while '0' <= self.char <= '9':
            buffer.append(self.char)
            self._current += 1
        if buffer:
            self._current -= 1
        return "".join(buffer)

    def _get_number(self):
        buffer = []
        left = self._get_integer10()
        if not left:
            if self.char != '.':
                raise ValueError(f"Expected a number, got \'{self.char}\'")
        else:
            buffer.append(left)
            self._current += 1
        if self.char == '.':
            buffer.append(self.char)
            self._current += 1
            right = self._get_integer10()
            if right:
                buffer.append(right)
            else:
                self._current -= 1
        else:
            self._current -= 1
        return "".join(buffer)

    def advance(self):
        self._token = None
        try:
            while self._current >= 0:
                char = self.char

                if char == '\n':
                    if self[TokenizerOptions.EmitNewLine]:
                        return self._create_token(TokenType.NewLine, char)
                    else:
                        self._next_char(char)
                        self._current += 1
                        continue

                if char in {' ', '\t'}:
                    if self[TokenizerOptions.EmitWhiteSpace]:
                        return self._create_token(TokenType.WhiteSpace, char)
                    else:
                        self._next_char(char)
                        self._current += 1
                        continue

                if char == ';':
                    if self[TokenizerOptions.EmitComments]:
                        if not self[TokenizerOptions.IncludeCommentCharacter]:
                            self._current += 1
                        return self._create_token(TokenType.Comment, self._get_line_comment())
                    else:
                        while self.char != '\n':
                            self._current += 1
                    continue
                if char == '(':
                    return self._create_token(TokenType.LeftCurvyBracket, char)
                if char == ')':
                    return self._create_token(TokenType.RightCurvyBracket, char)
                if char == '{':
                    return self._create_token(TokenType.LeftCurlyBracket, char)
                if char == '}':
                    return self._create_token(TokenType.RightCurlyBracket, char)
                if char == ',':
                    return self._create_token(TokenType.Comma, char)
                if char == '.':
                    if self.next_char.isdigit():
                        return self._create_token(TokenType.Literal_Float, self._get_number())
                    return self._create_token(TokenType.Dot, char)
                if char == ':':
                    return self._create_token(TokenType.Colon, char)
                if char == '\'':
                    self._current += 1
                    char = self.char
                    self._current += 1
                    if char == "\\":
                        escaped = self._get_special_character(self.char)
                        if escaped:
                            self._current += 1
                            char = escaped
                    if self.char != '\'':
                        raise ValueError(f"Invalid char literal: \'{char + self.char}\' at line {self._line}, char {self._char}")
                    # self._current += 1
                    return self._create_token(TokenType.Literal_Char, char)
                if char == '\"':
                    self._current += 1
                    buffer = []
                    while self.char != '\"':
                        char = self.char
                        self._current += 1
                        if char == "\\":
                            escaped = self._get_special_character(self.char)
                            if escaped:
                                char = escaped
                                self._current += 1
                        buffer.append(char)
                    # self._current += 1
                    return self._create_token(TokenType.Literal_String, "".join(buffer))
                if char == '\\':
                    self._current += 1
                    if self.char == 'x':
                        return self._create_token(TokenType.Literal_Hex, self._get_hex())
                    raise ValueError(f"Invalid number format: {self.char}")
                if char.isdigit() or char == '-':
                    number = self._get_number()
                    if '.' in number:
                        return self._create_token(TokenType.Literal_Float, number)
                    return self._create_token(TokenType.Literal_Int, number)

                return self._create_token(TokenType.Identifier, self._get_identifier())
        except IndexError:
            self._current = -1
            return self._create_token(TokenType.EOF, "")

    @staticmethod
    def _is_identifier_first_character(c: str):
        return c.isalpha() or c in {'_', '$', '#', '%', '!'}

    @staticmethod
    def _is_identifier_character(c: str):
        return c.isalnum() or c in {'_', '$', '#', '%', '!'}

    @staticmethod
    def _get_special_character(c: str):
        if c == 'r':
            return '\r'
        elif c == 't':
            return '\t'
        elif c == 'n':
            return '\n'
        elif c == '\\':
            return c
        elif c == '\'':
            return c
        else:
            return None

    def eat(self, value):
        if self[TokenizerOptions.SkipSpacesBeforeEating]:
            with self.options(TokenizerOptions.EmitWhiteSpace):
                while self.token == TokenType.WhiteSpace:
                    self.advance()
        if self._token != value:
            raise ValueError(f"Expected token {value}, got {self._token}")
        self.advance()

    def options(self, *args: TokenizerOptions):
        return self.TokenizerOptionsWrapper(self, *args)

    def __getitem__(self, item: TokenizerOptions) -> bool:
        return self._options[item]

    def __setitem__(self, key: TokenizerOptions, value: bool):
        if type(value) is not bool:
            raise TypeError(f"value must be of type {bool.__name__}")
        self._options[key] = value


if __name__ == '__main__':
    with open("../../tests/test1.qsm") as src:
        tokenizer = Tokenizer(src.read())
        with tokenizer.options() as options:
            while tokenizer.has_tokens:
                print(tokenizer.advance())
