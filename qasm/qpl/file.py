import sys
from enum import IntFlag
from io import BytesIO
from struct import Struct
from typing import Dict, BinaryIO, Union, Optional, SupportsInt


__all__ = [
    "FileFormatError",
    "Header",
    "QPLFile",
    "QPLFlags",
    "SectionTable",
    "SectionTableEntry",
    "read_file"
]


class FileFormatError(Exception):
    ...


class QPLFlags(IntFlag):
    HasEntryPoint = 1 << 0
    HasExports = 1 << 1
    RelativeAddressing = 1 << 2

    def __getitem__(self, item):
        if type(item) is str:
            return type(self)[item]


class ArchitectureInfo:
    ARCHITECTURE_MASK = 0x7F
    BYTE_ORDER_MASK = 0x80

    NATIVE_SIZE = Struct("P").size

    def __init__(self, arch: SupportsInt, little_endian: Optional[bool] = None) -> None:
        arch = int(arch)
        if not isinstance(arch, int):
            raise TypeError(f"arch must be an {int.__name__}, not a {type(arch).__name__}")
        if arch == 0:
            raise ValueError(f"arch must not be 0")
        if little_endian:
            if not isinstance(little_endian, bool):
                raise TypeError(f"little_endian must be a {bool.__name__}, not a {type(little_endian).__name__}")
            self._system_word_size = arch
            self._is_little_endian = little_endian
        else:
            # MSB indicates byte order (0 = little-endian, 1 = big-endian)
            self._system_word_size = arch & self.ARCHITECTURE_MASK
            self._is_little_endian = (arch & self.BYTE_ORDER_MASK) == 0
        self._architecture = 8 * self._system_word_size

    @property
    def is_little_endian(self) -> bool:
        return self._is_little_endian

    @property
    def is_big_endian(self) -> bool:
        return not self._is_little_endian

    @property
    def system_word_size(self) -> int:
        return self._system_word_size

    @property
    def architecture(self) -> int:
        return self._architecture

    @classmethod
    def get_native_architecture_info(cls):
        return cls(cls.NATIVE_SIZE, sys.byteorder == "little")

    def __int__(self) -> int:
        return (self.is_big_endian & self.BYTE_ORDER_MASK) | (self._system_word_size & self.ARCHITECTURE_MASK)

    def __str__(self) -> str:
        return f"{self._architecture} bit, {'big' if self.is_big_endian else 'little'}-endian"


class Header:
    """format is

    Signature  (4 bytes) - must be "QPL\\\\0"

    -- 4 byte mark (4 bytes)

    Flags (1 byte)

    Architecture (1 byte)

    Number of Section Entries (1 byte)

    RESERVED (1 byte)

    -- 4 byte mark (8 bytes)

    Version.Major (2 bytes)

    Version.Minor (2 bytes)

    -- 4 byte mark (12 bytes)

    RESERVED (4 bytes)

    -- 4 byte mark (total 16 bytes)

    for a total of a 16-byte header"""
    FORMAT = "4s b b b x h h 4x"
    STRUCT = Struct(FORMAT)
    SIGNATURE = b"QPL\0"

    def __init__(self, flags: Union[QPLFlags, int], architecture: Union[int, ArchitectureInfo], num_sections: int, version_major: int, version_minor: int):
        self._flags = QPLFlags(flags)
        self._architecture = ArchitectureInfo(architecture)
        self._num_sections = num_sections
        self._version = version_major, version_minor

    @property
    def flags(self) -> int:
        return self._flags

    @property
    def architecture(self):
        return self._architecture

    def has_flag(self, flag: QPLFlags):
        return bool(self._flags & flag)

    @property
    def num_sections(self):
        return self._num_sections

    @property
    def version(self):
        return self._version

    def to_bytes(self):
        return self.STRUCT.pack(self.SIGNATURE, self._flags, int(self._architecture), self._num_sections, *self._version)

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < cls.STRUCT.size:
            raise ValueError(f"len(data) must be >= {cls.STRUCT.size}")
        signature, *args = cls.STRUCT.unpack(data)
        if signature != cls.SIGNATURE:
            raise ValueError(f"Signature must be {cls.SIGNATURE}, but it was {signature}")
        return cls(*args)

    @classmethod
    def from_binary_io(cls, io: BinaryIO):
        return cls.from_bytes(io.read(cls.STRUCT.size))

    def __str__(self):
        return '\n'.join((
            "[QPL Header]",
            f"Flags: {self.flags}",
            f"Architecture: {self._architecture}",
            '\n'.join(map(lambda flag: f"[Flag] {flag.name}: {self.has_flag(flag)}", QPLFlags)),
            f"Section Count: {self.num_sections}",
            f"Language Version: {'.'.join(map(str, self._version))}"
        ))


class SectionTableEntry:
    """format is
    Name (8 bytes) - name of the section
    Size (4 bytes) - size of the section
    Offset (4 bytes) - 4 byte relative address of the section
    """
    MAX_SECTION_NAME_LENGTH = 8
    FORMAT = f"{MAX_SECTION_NAME_LENGTH}s i i"
    STRUCT = Struct(FORMAT)

    def __init__(self, name: str, size: int, offset: int):
        if len(name) > self.MAX_SECTION_NAME_LENGTH:
            raise IndexError(f"Name of section must be <= {self.MAX_SECTION_NAME_LENGTH} (was \"{name}\", len={len(name)})")
        self._name = name
        self._size = size
        self._offset = offset

    @property
    def name(self):
        return self._name

    @property
    def size(self):
        return self._size

    @property
    def offset(self):
        return self._offset

    def to_bytes(self):
        return self.STRUCT.pack(self._name.encode("ascii"), self._size, self._offset)

    @classmethod
    def from_bytes(cls, data: bytes):
        if len(data) < cls.STRUCT.size:
            raise FileFormatError(f"len(data) must be >= {cls.STRUCT.size}")
        name, *args = cls.STRUCT.unpack(data)
        name = name.decode("ascii").strip("\0")
        return cls(name, *args)

    @classmethod
    def from_binary_io(cls, io: BinaryIO):
        return cls.from_bytes(io.read(cls.STRUCT.size))

    def __str__(self):
        return '\n'.join((
            f"[Section Entry]",
            f"Section Name: {self._name}",
            f"Section Size: {self._size}",
            f"Section Offset: {self._offset}"
        ))


class SectionTable:
    def __init__(self):
        self._entries: Dict[str, SectionTableEntry] = {}

    @property
    def section_names(self):
        return tuple(self._entries.keys())

    @property
    def entries(self):
        return tuple(self._entries.values())

    def add_entry(self, entry: SectionTableEntry):
        if not isinstance(entry, SectionTableEntry):
            raise TypeError(f"entry must be an instance of {SectionTableEntry}")
        if entry.name in self._entries:
            raise KeyError(f"Section {entry.name} entry already exists in the table")
        self._entries[entry.name] = entry

    def get_entry(self, name: str):
        return self._entries[name]

    def set_entry(self, entry: SectionTableEntry):
        if not isinstance(entry, SectionTableEntry):
            raise TypeError(f"entry must be an instance of {SectionTableEntry}")
        self._entries[entry.name] = entry

    def __getitem__(self, item):
        return self.get_entry(item)

    def to_bytes(self):
        return sum(map(SectionTableEntry.to_bytes, self._entries.values()), b"")


class QPLFile:
    def __init__(self, header: Optional[Header] = None):
        self._header = header
        self._section_table = SectionTable()
        self._sections: Dict[str, bytes] = {}

    @property
    def header(self):
        return self._header

    @property
    def sections(self):
        return self._sections

    @property
    def section_table(self):
        return self._section_table

    @property
    def size(self):
        return sum(map(len, self._sections.values()))

    @property
    def raw_data(self):
        return b"".join(self._sections.values())

    def add_section(self, name: str, data: bytes):
        if not name:
            raise ValueError(f"name can't be empty")
        if len(name) > SectionTableEntry.MAX_SECTION_NAME_LENGTH:
            raise IndexError(f"len(name) must be < {SectionTableEntry.MAX_SECTION_NAME_LENGTH}")
        if name in self._sections:
            raise KeyError(f"Section \"{name}\" is already defined")
        self._sections[name] = data
        self._section_table.add_entry(SectionTableEntry(name, len(data), 0))

    def calculate_section_offsets(self):
        offset = Header.STRUCT.size + SectionTableEntry.STRUCT.size * len(self._sections)
        for name, data in self._sections.items():
            entry = SectionTableEntry(name, len(data), offset)
            self._section_table.set_entry(entry)
            offset += entry.size

    def to_bytes(self, *header_options):
        data = bytearray()

        self._header = Header(*header_options, len(self._sections), 1, 0)
        data.extend(self._header.to_bytes())

        self.calculate_section_offsets()

        for entry in self._section_table.entries:
            data.extend(entry.to_bytes())

        for section_data in self._sections.values():
            data.extend(section_data)

        return bytes(data)

    def write(self, path: str, *header_options):
        with open(path, "wb") as dst:
            self.write_to(dst, *header_options)

    def write_to(self, io: BinaryIO, *header_options):
        io.write(self.to_bytes(*header_options))

    @classmethod
    def from_bytes(cls, data: bytes):
        return cls.from_binary_io(BytesIO(data))

    @classmethod
    def from_binary_io(cls, io: BinaryIO):
        header = Header.from_binary_io(io)
        file = QPLFile(header)

        entries = [SectionTableEntry.from_binary_io(io) for _ in range(header.num_sections)]

        for entry in entries:
            io.seek(entry.offset)
            section_data = io.read(entry.size)
            file.add_section(entry.name, section_data)

        file.calculate_section_offsets()

        return file

    def __str__(self):
        return (
            f"[QPL File]\n" +
            str(self._header) +
            "\n\n\n" +
            "\n\n".join(map(str, self._section_table.entries))
        )


def read_file(path: str):
    with open(path, "rb") as src:
        return QPLFile.from_binary_io(src)


if __name__ == '__main__':
    print("Native Architecture Info:", ArchitectureInfo.get_native_architecture_info(), '\n')
    with open("../../tests/test2.qpl", "rb") as src:
        qpl_file = QPLFile.from_binary_io(src)
        print(qpl_file)
        # print()
        # print()
        # print(*list(map(lambda x: hex(x)[2:].zfill(2), qpl_file.to_bytes())))
