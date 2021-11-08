from enum import Enum
from typing import Type


__all__ = [
    "IConfigurable"
]


class IConfigurable:
    _OptionType = None

    class ConfigurationOptionWrapper:
        def __init__(self, owner, *options: "IConfigurable._OptionType", default: bool = False):
            if not all(map(lambda o: isinstance(o, IConfigurable._OptionType), options)):
                raise TypeError(f"all options must be instances of {IConfigurable._OptionType}")
            self._owner = owner
            self._options = options
            self._value = default

        def disabled(self):
            self._value = False
            return self

        def enabled(self):
            self._value = True
            return self

        def set_to(self, value: bool):
            if not isinstance(value, bool):
                raise TypeError(f"option value must be a bool")
            self._value = value
            return self

        def __class_getitem__(cls, item):
            if not issubclass(item, type):
                raise TypeError(f"item must be a type")
            cls._Type = item
            return cls

        def __enter__(self):
            for option in self._options:
                self._owner[option] = self._value
            return self._owner

        def __exit__(self, exc_type, exc_val, exc_tb):
            for option in self._options:
                self._owner[option] = not self._value
            return False

    def __init__(self):
        self._options = {
            key: False for key in self._OptionType
        }

    def options(self, *options: Type[_OptionType]):
        if not len(options):
            return self._options
        return self.ConfigurationOptionWrapper(self, *options)

    def __class_getitem__(cls, item: Type[Enum]):
        if not issubclass(item, Enum):
            raise TypeError(f"item must be a type deriving from {Enum}")
        cls._OptionType = item
        return cls

    def __init_subclass__(cls):
        setattr(cls, "_OptionType", cls._OptionType)

    def __getitem__(self, item: _OptionType):
        return self._options[item]

    def __setitem__(self, item: _OptionType, value: bool):
        if not isinstance(value, bool):
            raise TypeError(f"option value must be a bool")
        self._options[item] = value
