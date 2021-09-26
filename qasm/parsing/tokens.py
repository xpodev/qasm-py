from enum import IntEnum


class TokenType(IntEnum):
    WhiteSpace = -4
    NewLine = -3
    Comment = -2

    Unknown = -1
    EOF = 0
    Dot = 1
    Identifier = 2

    LiteralIndicator_Minimum = 4
    Literal_Char = 4
    Literal_Int = 5
    Literal_String = 6
    Literal_Bool = 7
    Literal_Float = 8
    Literal_Null = 9
    Literal_Bytes = 10
    Literal_Hex = 11
    LiteralIndicator_Maximum = 11

    Comma = 20
    LeftCurlyBracket = 21
    RightCurlyBracket = 22
    LeftCurvyBracket = 23
    RightCurvyBracket = 24
    Colon = 25

    def is_literal(self):
        return self.LiteralIndicator_Minimum <= self <= self.LiteralIndicator_Maximum
