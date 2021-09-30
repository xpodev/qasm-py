from abc import ABC, abstractmethod
from enum import IntEnum

try:
    from .document import Document
    from .itokenizer import ITokenizer
    from ..iconfigurable import IConfigurable
except ImportError:
    from qasm.parsing.document import Document
    from qasm.iconfigurable import IConfigurable
    from qasm.parsing.itokenizer import ITokenizer


__all__ = [
    "IParser"
]


class ParserOptions(IntEnum):
    AllowFunctionModifiers = 0
    AllowVariableModifiers = 1


class IParser(ABC, IConfigurable[ParserOptions]):
    @abstractmethod
    def parse(self, tokenizer: ITokenizer) -> Document:
        """
        Parses an iterable of tokens and returns a document.
        :param tokenizer: The tokenizer to read tokens from.
        :return: The document built from the tokens.
        """
        ...
