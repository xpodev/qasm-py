__all__ = [
    "Label",
    "LabelReference"
]


class LabelReference:
    def __init__(self, name: str):
        self._name = name

    @property
    def name(self):
        return self._name


class Label(LabelReference):
    def __init__(self, name: str, offset: int):
        super().__init__(name)
        self._offset = offset

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value: int):
        self._offset = value
