from abc import ABC, abstractmethod
from typing import Iterable

from qasm.parsing.nodes import Node
from qasm.parsing.itokenizer import ITokenizer
from qasm.parsing.tokens import TokenType
from qasm.parsing.asm_token import Token


class IParser(ABC):
    @abstractmethod
    def parse(self) -> Iterable[Node]:
        ...

    @property
    @abstractmethod
    def tokenizer(self) -> ITokenizer:
        ...

    @abstractmethod
    def get_token(self, typ: TokenType) -> Token:
        ...
