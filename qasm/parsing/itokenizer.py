from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Union, Optional

from qasm.parsing.asm_token import Token, TokenType


__all__ = [
    "ITokenizer",
    "TokenizerOptions",
    "UnexpectedCharacterError",
    "UnexpectedTokenError"
]


class TokenizerOptions(IntEnum):
    """
    Defines options for the tokenizer to change the behaviour of the tokenizer at runtime
    """
    EmitNewLine = 1
    SkipSpacesBeforeEating = 2
    EmitWhiteSpace = 3
    EmitComments = 4
    IncludeCommentCharacter = 5
    IncludeCommentEOL = 6


class UnexpectedCharacterError(Exception):
    """
    An error that is thrown when a tokenizer matches a character it couldn't tokenize
    """
    def __init__(self, expected: Optional[str], got: str, line: int, character: int):
        """
        :param expected: The character the tokenizer expected to get or `None` if the tokenizer got an unrecognized character.
        :param got: The character the tokenizer got.
        :param line: The line at which the character is located.
        :param character: The position of the character in the line at which the character is located.
        """
        if expected:
            super().__init__(f"Expected \'{expected}\', got \'{got}\' (at line {line}, character {character})")
        else:
            super().__init__(f"Unexpected character \'{got}\' (at line {line}, character {character})")
        self._expected = expected
        self._got = got
        self._line = line
        self._character = character

    @property
    def expected(self) -> Optional[str]:
        """
        :return: The character the tokenizer expected to get or `None` if the tokenizer got an unrecognized character.
        """
        return self._expected

    @property
    def got(self) -> str:
        """
        :return: The character the tokenizer got.
        """
        return self._got

    @property
    def line(self) -> int:
        """
        :return: The line at which the character is located.
        """
        return self._line

    @property
    def character(self) -> int:
        """
        :return: The position of the character in the line at which the character is located.
        """
        return self._character


class UnexpectedTokenError(Exception):
    """
    An error that is thrown when a tokenizer tried to consume a token of the wrong type.
    """
    def __init__(self, expected: Union[TokenType, str], got: Token) -> None:
        """
        :param expected: The token type / value the tokenizer expected to get.
        :param got: The actual token the tokenizer got.
        """
        super().__init__(f"Expected token \"{expected.name if isinstance(expected, TokenType) else expected}\", got \"{got.type.name}\" (at line {got.line}, character {got.char})")
        self._expected = expected
        self._got = got

    @property
    def expected(self) -> Union[TokenType, str]:
        """
        :return: The token type / value the tokenizer expected to get.
        """
        return self._expected

    @property
    def got(self) -> Token:
        """
        :return: The actual token the tokenizer got.
        """
        return self._got


class ITokenizer(ABC):
    """
    An interface for any object that can supply tokens to an object of type `IParser`
    """
    @property
    @abstractmethod
    def has_tokens(self) -> bool:
        """
        :return: Whether or not the tokenizer has more tokens to extract.
        """
        ...

    @property
    @abstractmethod
    def token(self) -> Token:
        """
        :return Current token (last token that was created).
        """
        ...

    @abstractmethod
    def advance(self) -> Token:
        """
        Searches the source for the next token and return it.
        This also sets `Token.token`

        :return: The next token in the source.
        """
        ...

    @abstractmethod
    def eat(self, value: Union[str, TokenType]) -> Token:
        """
        Consumes the current token if it matches the specified value. An exception is thrown otherwise.

        :param value: The value the current token should match.
        :return: The next token in the source (see `ITokenizer.advance()`)
        :raise UnexpectedTokenError if the current token didn't match the specified value
        """
        ...

    @abstractmethod
    def __getitem__(self, item: TokenizerOptions) -> bool:
        """
        Get the current status of an option for this tokenizer.

        :param item: The name of the option.
        :return: The status of the option.
        """
        ...

    @abstractmethod
    def __setitem__(self, key: TokenizerOptions, value: bool) -> None:
        """
        Sets the current status of an option for this tokenizer.

        :param key: The name of the option to set.
        :param value: The new status of the option to set.
        """
        ...
