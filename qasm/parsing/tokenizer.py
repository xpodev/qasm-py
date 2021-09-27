from typing import Union, Set, Optional

from qasm.parsing.itokenizer import *


__all__ = [
    "Token",
    "Tokenizer",
    "TokenizerOptions",
    "TokenType",
    "UnexpectedCharacterError",
    "UnexpectedTokenError"
]


class Tokenizer(ITokenizer):
    class TokenizerOptionsWrapper:
        def __init__(self, tokenizer, *opt: TokenizerOptions) -> None:
            self._tokenizer = tokenizer
            self._options = set(opt)

        def set_options(self, *args: TokenizerOptions) -> None:
            self._options = set(args)

        def options(self, value: bool) -> None:
            for option in self._options:
                self._tokenizer[option] = value

        def __enter__(self):
            self.options(True)
            return self._tokenizer

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            self.options(False)
            return False

    def __init__(self, source: str) -> None:
        self._source = source
        self._token = None
        self._current = 0
        self._line = self._last_line = 1
        self._char = self._last_char = 1
        self._options = {
            key: False for key in TokenizerOptions
        }
        self._chars_allowed_at_beginning_of_identifier: Set[str] = {'_', '$', '#', '%', '!'}
        self._chars_allowed_in_identifier: Set[str] = self._chars_allowed_at_beginning_of_identifier

    @property
    def current_char(self) -> str:
        try:
            return self._source[self._current]
        except IndexError:
            return ""

    @property
    def has_tokens(self) -> bool:
        return self._current >= 0 and self._token != TokenType.EOF

    @property
    def next_char(self) -> str:
        try:
            return self._source[self._current + 1]
        except IndexError:
            return ""

    @property
    def token(self) -> Token:
        return self._token

    def _create_token(self, typ: TokenType, value: str) -> Token:
        self._token = Token(self._last_line, self._last_char, typ, value)
        self._last_line = self._line
        self._last_char = self._char
        return self._token

    def _create_unexpected_character_error(self, expected: Union[str, TokenType]) -> UnexpectedCharacterError:
        if isinstance(expected, TokenType):
            expected = expected.name
        return UnexpectedCharacterError(expected, self.current_char, self._line, self._char)

    def _get_identifier(self) -> str:
        if self._is_identifier_first_character(self.current_char):
            buffer = []
        else:
            raise self._create_unexpected_character_error(TokenType.Identifier)
        while self._is_identifier_character(self.current_char):
            buffer.append(self.get_current_char())
        return "".join(buffer)

    def _get_integer10(self) -> str:
        buffer = []
        if self.current_char == '-':
            buffer.append(self.get_current_char())
        while '0' <= self.current_char <= '9':
            buffer.append(self.get_current_char())
        return "".join(buffer)

    def _get_integer16(self) -> str:
        buffer = []
        while '0' <= self.current_char <= '9' or 'a' <= self.current_char.lower() <= 'f':
            buffer.append(self.get_current_char())
        return "".join(buffer)

    def _get_line_comment(self) -> str:
        buffer = []
        try:
            while self.next_char != '\n':
                buffer.append(self.get_current_char())
            if self[TokenizerOptions.IncludeCommentEOL]:
                buffer.append(self.get_current_char())
        except IndexError:
            ...
        return "".join(buffer)

    def _get_number(self) -> str:
        buffer = []
        left = self._get_integer10()
        if not left:
            if self.current_char != '.':
                raise self._create_unexpected_character_error('.')
        else:
            buffer.append(left)
        if self.current_char == '.':
            buffer.append(self.get_current_char())
            right = self._get_integer10()
            if right:
                buffer.append(right)
        return "".join(buffer)

    def _is_identifier_character(self, c: str) -> bool:
        return c.isalnum() or c in self._chars_allowed_in_identifier

    def _is_identifier_first_character(self, c: str) -> bool:
        return c.isalpha() or c in self._chars_allowed_at_beginning_of_identifier

    def _next_char(self, c: str) -> None:
        if c == '\n':
            self._line += 1
            self._char = 0
        elif c == '\r':
            self._char = 0
        self._char += 1

    def _next_string(self, s: str) -> None:
        list(map(self._next_char, s))

    def advance(self) -> Token:
        self._token = None
        while self.has_tokens:
            char = self.current_char

            if not char:
                break

            if char == '\n':
                if self[TokenizerOptions.EmitNewLine]:
                    return self._create_token(TokenType.NewLine, self.get_current_char())
                else:
                    self._create_token(TokenType.NewLine, self.get_current_char())
                    continue

            if char in {' ', '\t'}:
                if self[TokenizerOptions.EmitWhiteSpace]:
                    return self._create_token(TokenType.WhiteSpace, self.get_current_char())
                else:
                    self._create_token(TokenType.WhiteSpace, self.get_current_char())
                    continue

            if char == ';':
                if self[TokenizerOptions.EmitComments]:
                    if not self[TokenizerOptions.IncludeCommentCharacter]:
                        self.get_current_char()
                    return self._create_token(TokenType.Comment, self._get_line_comment())
                else:
                    while self.get_current_char() != '\n':
                        ...
                continue
            if char == '(':
                return self._create_token(TokenType.LeftCurvyBracket, self.get_current_char())
            if char == ')':
                return self._create_token(TokenType.RightCurvyBracket, self.get_current_char())
            if char == '{':
                return self._create_token(TokenType.LeftCurlyBracket, self.get_current_char())
            if char == '}':
                return self._create_token(TokenType.RightCurlyBracket, self.get_current_char())
            if char == ',':
                return self._create_token(TokenType.Comma, self.get_current_char())
            if char == '.':
                if self.next_char.isdigit():
                    return self._create_token(TokenType.Literal_Float, self._get_number())
                return self._create_token(TokenType.Dot, self.get_current_char())
            if char == ':':
                return self._create_token(TokenType.Colon, self.get_current_char())
            if char == '\'':
                self.get_current_char()
                char = self.get_current_char()
                if char == "\\":
                    escaped = self._get_special_character(self.current_char)
                    if escaped:
                        char = escaped
                if self.get_current_char() != '\'':
                    raise self._create_unexpected_character_error('\'')
                return self._create_token(TokenType.Literal_Char, char)
            if char == '\"':
                self.get_current_char()
                buffer = []
                while self.current_char != '\"':
                    char = self.get_current_char()
                    if char == "\\":
                        escaped = self._get_special_character(self.current_char)
                        if escaped:
                            char = escaped
                            self._current += 1
                    buffer.append(char)
                self.get_current_char()
                return self._create_token(TokenType.Literal_String, "".join(buffer))
            if char == '\\':
                self.get_current_char()
                if self.get_current_char() == 'x':
                    return self._create_token(TokenType.Literal_Hex, self._get_integer16())
                raise self._create_unexpected_character_error('x')
            if char.isdigit() or char == '-':
                number = self._get_number()
                return self._create_token(TokenType.Literal_Float if '.' in number else TokenType.Literal_Int, number)
            if self._is_identifier_first_character(char):
                return self._create_token(TokenType.Identifier, self._get_identifier())

            raise self._create_unexpected_character_error(f"not \"{char}\"")
        return self._create_token(TokenType.EOF, "<EOF>")

    def eat(self, value: Union[TokenType, str]) -> Token:
        if self[TokenizerOptions.SkipSpacesBeforeEating]:
            with self.options(TokenizerOptions.EmitWhiteSpace):
                while self._token == TokenType.WhiteSpace:
                    self.advance()
        if self._token != value:
            raise UnexpectedTokenError(value, self._token)
        return self.advance()

    def get_current_char(self) -> str:
        char = self.current_char
        self._next_char(char)
        self._current += 1
        return char

    def options(self, *args: TokenizerOptions) -> TokenizerOptionsWrapper:
        return self.TokenizerOptionsWrapper(self, *args)

    @staticmethod
    def _get_special_character(c: str) -> Optional[str]:
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

    def __getitem__(self, item: TokenizerOptions) -> bool:
        return self._options[item]

    def __setitem__(self, key: TokenizerOptions, value: bool) -> None:
        if type(value) is not bool:
            raise TypeError(f"value must be of type {bool.__name__}")
        self._options[key] = value


if __name__ == '__main__':
    with open("../../tests/hello_world.qsm") as src:
        _tokenizer = Tokenizer(src.read())
        with _tokenizer.options() as options:
            while _tokenizer.has_tokens:
                print(_tokenizer.advance())
