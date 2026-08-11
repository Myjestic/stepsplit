"""Disk-backed data structures: structure database, offset index, bitset, queue.

None of these structures keep the STEP file itself in memory. The offset index
is a dense little-endian ``uint64`` array addressed by entity id, so files with
non-ascending entity ids are supported.
"""

from __future__ import annotations

import mmap
import os
import sqlite3
import struct
from pathlib import Path
from typing import Iterable, Iterator

STRUCTURE_DB = "structure.sqlite"
OFFSETS_FILE = "offsets.u64"
CANDIDATES_FILE = "backward_candidates.u64"

_ENTRY = struct.Struct("<Q")
_GROWTH_SLACK = 1 << 20


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=FILE;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id  INTEGER PRIMARY KEY,
    ident       TEXT NOT NULL,
    name        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS products_name_idx ON products(name);

CREATE TABLE IF NOT EXISTS formations (
    formation_id INTEGER PRIMARY KEY,
    product_id   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS formations_product_idx ON formations(product_id);

CREATE TABLE IF NOT EXISTS product_definitions (
    pd_id        INTEGER PRIMARY KEY,
    formation_id INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS product_definitions_formation_idx
    ON product_definitions(formation_id);

CREATE TABLE IF NOT EXISTS usages (
    usage_id    INTEGER PRIMARY KEY,
    parent_pd   INTEGER NOT NULL,
    child_pd    INTEGER NOT NULL,
    usage_type  TEXT NOT NULL,
    designator  TEXT NOT NULL DEFAULT '',
    parse_mode  TEXT NOT NULL DEFAULT 'positional'
);
CREATE INDEX IF NOT EXISTS usages_parent_idx ON usages(parent_pd);
CREATE INDEX IF NOT EXISTS usages_child_idx ON usages(child_pd);

CREATE TABLE IF NOT EXISTS definition_shapes (
    pds_id        INTEGER PRIMARY KEY,
    definition_id INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS definition_shapes_definition_idx
    ON definition_shapes(definition_id);

CREATE TABLE IF NOT EXISTS shape_representations (
    sdr_id            INTEGER PRIMARY KEY,
    pds_id            INTEGER NOT NULL,
    representation_id INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS shape_representations_pds_idx
    ON shape_representations(pds_id);

CREATE TABLE IF NOT EXISTS context_shapes (
    cdsr_id         INTEGER PRIMARY KEY,
    relationship_id INTEGER NOT NULL,
    pds_id          INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS context_shapes_pds_idx ON context_shapes(pds_id);
"""


def structure_db_path(work_dir: Path) -> Path:
    return work_dir / STRUCTURE_DB


def offsets_path(work_dir: Path) -> Path:
    return work_dir / OFFSETS_FILE


def candidates_path(work_dir: Path) -> Path:
    return work_dir / CANDIDATES_FILE


class CandidateList:
    """Append-only list of entity ids that may be needed by a backward pass.

    Stored as little-endian ``uint64`` values so a finished index can drive the
    export without rescanning the whole STEP file for styles and solids.
    """

    def __init__(self, path: Path, append: bool = False) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if append and path.exists():
            self.count = path.stat().st_size // 8
            self._handle = path.open("ab")
        else:
            self.count = 0
            self._handle = path.open("wb")

    def add(self, entity_id: int) -> None:
        self._handle.write(_ENTRY.pack(entity_id))
        self.count += 1

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        try:
            self._handle.flush()
        finally:
            self._handle.close()

    def __enter__(self) -> "CandidateList":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @staticmethod
    def iter_ids(path: Path) -> Iterator[int]:
        if not path.exists():
            return
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1 << 20)
                if not chunk:
                    return
                for index in range(0, len(chunk) - (len(chunk) % 8), 8):
                    yield _ENTRY.unpack_from(chunk, index)[0]

    @staticmethod
    def available(work_dir: Path) -> bool:
        path = candidates_path(work_dir)
        return path.exists() and path.stat().st_size >= 8


def connect(work_dir: Path, create: bool = False) -> sqlite3.Connection:
    path = structure_db_path(work_dir)
    if not create and not path.exists():
        raise FileNotFoundError(path)
    work_dir.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(SCHEMA)
    return connection


def connect_readonly(work_dir: Path) -> sqlite3.Connection:
    """Open the structure DB without creating or migrating schema."""
    path = structure_db_path(work_dir)
    if not path.exists():
        raise FileNotFoundError(path)
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def read_meta(connection: sqlite3.Connection) -> dict[str, str]:
    return {key: value for key, value in connection.execute("SELECT key,value FROM meta")}


def write_meta(connection: sqlite3.Connection, values: dict[str, object]) -> None:
    connection.executemany(
        "INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
        [(key, str(value)) for key, value in values.items()],
    )


class OffsetIndex:
    """Dense ``entity_id -> byte offset`` map stored in a growable mmap file.

    Slot ``0`` means "unknown", therefore offsets are stored incremented by one.
    """

    def __init__(self, path: Path, capacity: int = 0, readonly: bool = False) -> None:
        self.path = path
        self.readonly = readonly
        if readonly:
            self._handle = path.open("rb")
            self._map = mmap.mmap(self._handle.fileno(), 0, access=mmap.ACCESS_READ)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.touch()
            self._handle = path.open("r+b")
            size = max(path.stat().st_size, (capacity + 1) * 8, 8)
            self._handle.truncate(size)
            self._handle.flush()
            self._map = mmap.mmap(self._handle.fileno(), size)
        self.capacity = len(self._map) // 8 - 1

    def _grow(self, entity_id: int) -> None:
        size = (entity_id + 1) * 8 + _GROWTH_SLACK
        size = max(size, len(self._map) * 2)
        self._map.flush()
        self._map.close()
        self._handle.truncate(size)
        self._handle.flush()
        self._map = mmap.mmap(self._handle.fileno(), size)
        self.capacity = size // 8 - 1

    def set(self, entity_id: int, offset: int) -> None:
        if entity_id > self.capacity:
            self._grow(entity_id)
        _ENTRY.pack_into(self._map, entity_id * 8, offset + 1)

    def get(self, entity_id: int) -> int | None:
        if entity_id > self.capacity or entity_id < 0:
            return None
        value = _ENTRY.unpack_from(self._map, entity_id * 8)[0]
        return value - 1 if value else None

    def flush(self) -> None:
        if not self.readonly:
            self._map.flush()

    def close(self) -> None:
        try:
            self.flush()
        finally:
            self._map.close()
            self._handle.close()

    def __enter__(self) -> "OffsetIndex":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class BitSet:
    """File-backed bitset; roughly 20 MB for 165 million entity ids."""

    def __init__(self, path: Path, max_id: int, reuse: bool = False) -> None:
        self.path = path
        self.size = max(max_id // 8 + 1, 1)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not (reuse and path.exists() and path.stat().st_size >= self.size):
            with path.open("wb") as handle:
                handle.truncate(self.size)
        self._handle = path.open("r+b")
        self._map = mmap.mmap(self._handle.fileno(), self.size)

    def add(self, value: int) -> bool:
        """Set the bit and report whether it was previously unset."""
        index, bit = divmod(value, 8)
        if index >= self.size:
            return False
        mask = 1 << bit
        current = self._map[index]
        if current & mask:
            return False
        self._map[index] = current | mask
        return True

    def __contains__(self, value: int) -> bool:
        index, bit = divmod(value, 8)
        if index >= self.size or value < 0:
            return False
        return bool(self._map[index] & (1 << bit))

    def iter_set(self) -> Iterator[int]:
        """Yield every set entity id without scanning a Python range."""
        data = self._map
        for byte_index in range(self.size):
            byte = data[byte_index]
            if not byte:
                continue
            base = byte_index << 3
            bit = 0
            while bit < 8:
                if byte & (1 << bit):
                    yield base + bit
                bit += 1

    def count(self) -> int:
        total = 0
        step = 1 << 20
        for start in range(0, self.size, step):
            total += sum(bin(byte).count("1") for byte in self._map[start : start + step])
        return total

    def flush(self) -> None:
        self._map.flush()

    def close(self) -> None:
        try:
            self._map.flush()
        finally:
            self._map.close()
            self._handle.close()

    def __enter__(self) -> "BitSet":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class DiskQueue:
    """Append-only FIFO of ``uint64`` values kept on disk.

    The read position is exposed so an interrupted traversal can be resumed.
    """

    def __init__(self, path: Path, resume: bool = False) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if resume and path.exists():
            self._handle = path.open("r+b")
        else:
            self._handle = path.open("w+b")
        self._handle.seek(0, os.SEEK_END)
        self._write_position = self._handle.tell()
        self.read_position = 0

    def __len__(self) -> int:
        return self._write_position // 8

    @property
    def pending(self) -> int:
        return (self._write_position - self.read_position) // 8

    def extend(self, values: Iterable[int]) -> None:
        payload = b"".join(_ENTRY.pack(value) for value in values)
        if not payload:
            return
        self._handle.seek(self._write_position)
        self._handle.write(payload)
        self._write_position += len(payload)

    def drain(self, batch: int = 65536) -> Iterator[int]:
        while self.read_position < self._write_position:
            self._handle.seek(self.read_position)
            payload = self._handle.read(min(batch * 8, self._write_position - self.read_position))
            self.read_position += len(payload)
            for index in range(0, len(payload), 8):
                yield _ENTRY.unpack_from(payload, index)[0]

    def flush(self) -> None:
        self._handle.flush()

    def close(self) -> None:
        try:
            self._handle.flush()
        finally:
            self._handle.close()

    def __enter__(self) -> "DiskQueue":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
