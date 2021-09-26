from qasm.parsing.tokens import TokenType


class Token:
    def __init__(self, line: int, char: int, type_: TokenType, value: str = None):
        self._line = line
        self._char = char
        self._type = type_
        self._value = value

    @property
    def line(self):
        return self._line

    @property
    def char(self):
        return self._char

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value

    def __eq__(self, other):
        if type(other) is str:
            return self._value == other
        if type(other) is int:
            return self._type.value == other
        if type(other) is TokenType:
            return self._type.value == other.value
        if type(other) is Token:
            return self._value == other.value and self._type == other.type
        raise TypeError(f"Incompatible types for operand (==): {Token} and {type(other)}")

    def __ne__(self, other):
        if type(other) is str:
            return self._value != other
        if type(other) is int:
            return self._type.value != other
        if type(other) is TokenType:
            return self._type.value != other.value
        if type(other) is Token:
            return self._value != other.value or self._type != other.type
        raise TypeError(f"Incompatible types for operator (!=): {Token} and {type(other)}")

    def __str__(self):
        return f"Token(Type={self._type.name}, line={self._line}, char={self._char})" if self._value is None else f"Token(Type={self._type.name}, value={self._value}, line={self._line}, char={self._char})"
