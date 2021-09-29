from abc import ABC, abstractmethod

from qasm.parsing.document import Document
from qasm.parsing.itokenizer import ITokenizer


__all__ = [
    "IParser"
]


class IParser(ABC):
    @abstractmethod
    def parse(self, tokenizer: ITokenizer) -> Document:
        """
        Parses an iterable of tokens and returns a document.
        :param tokenizer: The tokenizer to read tokens from.
        :return: The document built from the tokens.
        """
        ...
