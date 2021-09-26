from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Union

from qasm.parsing.asm_token import Token, TokenType


class TokenizerOptions(IntEnum):
    EmitNewLine = 1
    SkipSpacesBeforeEating = 2
    EmitWhiteSpace = 3
    EmitComments = 4
    IncludeCommentCharacter = 5
    IncludeCommentEOL = 6


class ITokenizer(ABC):
    @property
    @abstractmethod
    def token(self) -> Token:
        ...

    @property
    @abstractmethod
    def has_tokens(self) -> bool:
        ...

    @abstractmethod
    def advance(self) -> Token:
        ...

    @abstractmethod
    def eat(self, value: Union[str, TokenType]):
        ...

    @abstractmethod
    def __getitem__(self, item: TokenizerOptions) -> bool:
        ...

    @abstractmethod
    def __setitem__(self, key: TokenizerOptions, value: bool):
        ...
