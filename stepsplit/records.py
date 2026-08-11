"""Byte-oriented scanning and parsing of ISO 10303-21 clear text records.

Everything here works on ``bytes`` and never decodes the whole file. STEP
strings may contain raw bytes, so names are decoded with ``latin-1`` only when
they are handed to the user interface.
"""

from __future__ import annotations

import re
from typing import BinaryIO, Container, Iterator

REF_RE = re.compile(rb"#(\d+)", re.ASCII)

WHITESPACE = b" \t\r\n\f\v"
_WS_SET = frozenset(WHITESPACE)
_IDENT_SET = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")

_APOSTROPHE = 0x27
_SEMICOLON = 0x3B
_SLASH = 0x2F
_STAR = 0x2A
_OPEN = 0x28
_CLOSE = 0x29
_COMMA = 0x2C
_HASH = 0x23
_EQUALS = 0x3D

DEFAULT_CHUNK_SIZE = 8 << 20


def find_terminator(data: bytes, start: int = 0) -> int:
    """Return the index of the first record-terminating semicolon.

    Handles STEP strings (with ``''`` escapes) and ``/* */`` comments. Returns
    ``-1`` when the buffer holds no complete record.
    """
    i = start
    end = len(data)
    in_string = False
    in_comment = False
    while i < end:
        char = data[i]
        if in_comment:
            if char == _STAR and i + 1 < end and data[i + 1] == _SLASH:
                in_comment = False
                i += 2
                continue
        elif in_string:
            if char == _APOSTROPHE:
                if i + 1 < end and data[i + 1] == _APOSTROPHE:
                    i += 2
                    continue
                in_string = False
        else:
            if char == _APOSTROPHE:
                in_string = True
            elif char == _SLASH and i + 1 < end and data[i + 1] == _STAR:
                in_comment = True
                i += 2
                continue
            elif char == _SEMICOLON:
                return i
        i += 1
    return -1


def iter_records(
    handle: BinaryIO,
    start: int = 0,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[tuple[int, bytes]]:
    """Yield ``(byte_offset, record)`` pairs, streaming the file in chunks.

    ``byte_offset`` is the position of the first byte belonging to the record,
    including leading whitespace. ``record`` always ends with its semicolon.

    The fast path locates semicolons with :meth:`bytes.find` and decides string
    membership from apostrophe parity, which is correct because a ``''`` escape
    contributes two apostrophes. Records containing a comment opener fall back
    to :func:`find_terminator`.
    """
    handle.seek(start)
    pending = bytearray()
    pending_offset = start
    file_offset = start
    inside_string = False
    has_comment = False

    while True:
        chunk = handle.read(chunk_size)
        if not chunk:
            break
        chunk_base = file_offset
        file_offset += len(chunk)
        position = 0
        while True:
            semicolon = chunk.find(b";", position)
            segment = chunk[position:] if semicolon < 0 else chunk[position : semicolon + 1]
            if segment:
                if segment.count(b"'") & 1:
                    inside_string = not inside_string
                previous = len(pending)
                pending += segment
                if not has_comment and pending.find(b"/*", max(previous - 1, 0)) >= 0:
                    has_comment = True
            if semicolon < 0:
                break
            position = semicolon + 1

            if has_comment:
                # Comments may hide semicolons and unbalance apostrophe parity.
                while True:
                    terminator = find_terminator(pending)
                    if terminator < 0:
                        break
                    yield pending_offset, bytes(pending[: terminator + 1])
                    pending_offset += terminator + 1
                    del pending[: terminator + 1]
                has_comment = b"/*" in pending
                inside_string = not has_comment and bool(pending.count(b"'") & 1)
                continue

            if inside_string:
                continue

            yield pending_offset, bytes(pending)
            pending_offset = chunk_base + position
            pending.clear()

    if pending.strip():
        yield pending_offset, bytes(pending)


def skip_whitespace(data: bytes, index: int) -> int:
    """Skip whitespace and ``/* */`` comments.

    A record starts right behind the previous semicolon, so any comment written
    between two entities belongs to the record that follows it.
    """
    end = len(data)
    while index < end:
        char = data[index]
        if char in _WS_SET:
            index += 1
        elif char == _SLASH and index + 1 < end and data[index + 1] == _STAR:
            closing = data.find(b"*/", index + 2)
            index = end if closing < 0 else closing + 2
        else:
            break
    return index


def _head(record: bytes) -> tuple[int | None, int]:
    """Return ``(entity_id, index after '=')`` for an instance record."""
    index = skip_whitespace(record, 0)
    end = len(record)
    if index >= end or record[index] != _HASH:
        return None, -1
    index += 1
    start = index
    while index < end and 0x30 <= record[index] <= 0x39:
        index += 1
    if index == start:
        return None, -1
    entity_id = int(record[start:index])
    index = skip_whitespace(record, index)
    if index >= end or record[index] != _EQUALS:
        return None, -1
    return entity_id, index + 1


def record_id(record: bytes) -> int | None:
    """Return the ``#id`` of an entity instance record, or ``None``."""
    return _head(record)[0]


def payload_start(record: bytes) -> int:
    """Index of the first byte behind ``#id=``; ``-1`` for non-instance records."""
    return _head(record)[1]


def entity_refs(record: bytes) -> list[int]:
    """Return every ``#id`` referenced on the right hand side of the record."""
    start = payload_start(record)
    if start < 0:
        return []
    return [int(match.group(1)) for match in REF_RE.finditer(record, start)]


def parse_arguments(data: bytes, index: int) -> tuple[list[bytes], int]:
    """Parse a parenthesised argument list starting at ``data[index] == '('``."""
    end = len(data)
    index += 1
    arguments: list[bytes] = []
    start = index
    depth = 0
    while index < end:
        char = data[index]
        if char == _APOSTROPHE:
            index += 1
            while index < end:
                if data[index] == _APOSTROPHE:
                    if index + 1 < end and data[index + 1] == _APOSTROPHE:
                        index += 2
                        continue
                    break
                index += 1
            index += 1
            continue
        if char == _SLASH and index + 1 < end and data[index + 1] == _STAR:
            closing = data.find(b"*/", index + 2)
            index = end if closing < 0 else closing + 2
            continue
        if char == _OPEN:
            depth += 1
        elif char == _CLOSE:
            if depth == 0:
                argument = data[start:index].strip()
                if argument or arguments:
                    arguments.append(argument)
                return arguments, index + 1
            depth -= 1
        elif char == _COMMA and depth == 0:
            arguments.append(data[start:index].strip())
            start = index + 1
        index += 1
    arguments.append(data[start:].strip())
    return arguments, end


def parse_entity(record: bytes) -> list[tuple[str, list[bytes]]]:
    """Return ``[(TYPE_NAME, [raw_argument, ...]), ...]`` for one record.

    Simple instances yield a single pair. Complex instances such as
    ``#5=(A(...)B(...));`` yield one pair per sub-entity, in file order.
    Type names are read from the instance syntax only, so identifiers that
    appear inside string values are never mistaken for entity types.
    """
    start = payload_start(record)
    if start < 0:
        return []
    index = skip_whitespace(record, start)
    end = len(record)
    if index >= end:
        return []

    if record[index] == _OPEN:
        parsed: list[tuple[str, list[bytes]]] = []
        index += 1
        while index < end:
            index = skip_whitespace(record, index)
            if index >= end or record[index] == _CLOSE:
                break
            name_start = index
            while index < end and record[index] in _IDENT_SET:
                index += 1
            if index == name_start:
                break
            name = record[name_start:index].decode("ascii", "replace").upper()
            index = skip_whitespace(record, index)
            if index < end and record[index] == _OPEN:
                arguments, index = parse_arguments(record, index)
            else:
                arguments = []
            parsed.append((name, arguments))
        return parsed

    name_start = index
    while index < end and record[index] in _IDENT_SET:
        index += 1
    if index == name_start:
        return []
    name = record[name_start:index].decode("ascii", "replace").upper()
    index = skip_whitespace(record, index)
    if index < end and record[index] == _OPEN:
        arguments, _ = parse_arguments(record, index)
    else:
        arguments = []
    return [(name, arguments)]


def entity_types(record: bytes) -> list[str]:
    return [name for name, _ in parse_entity(record)]


def peek_type_names(record: bytes) -> set[str]:
    """Return entity type names without parsing arguments (cheap filter)."""
    start = payload_start(record)
    if start < 0:
        return set()
    index = skip_whitespace(record, start)
    end = len(record)
    if index >= end:
        return set()
    names: set[str] = set()
    if record[index] == _OPEN:
        index += 1
        while index < end:
            index = skip_whitespace(record, index)
            if index >= end or record[index] == _CLOSE:
                break
            name_start = index
            while index < end and record[index] in _IDENT_SET:
                index += 1
            if index == name_start:
                break
            names.add(record[name_start:index].decode("ascii", "replace").upper())
            index = skip_whitespace(record, index)
            if index < end and record[index] == _OPEN:
                depth = 1
                index += 1
                while index < end and depth:
                    char = record[index]
                    if char == 0x27:  # skip strings
                        index += 1
                        while index < end:
                            if record[index] == 0x27:
                                if index + 1 < end and record[index + 1] == 0x27:
                                    index += 2
                                    continue
                                index += 1
                                break
                            index += 1
                        continue
                    if char == _OPEN:
                        depth += 1
                    elif char == _CLOSE:
                        depth -= 1
                    index += 1
        return names
    name_start = index
    while index < end and record[index] in _IDENT_SET:
        index += 1
    if index == name_start:
        return set()
    return {record[name_start:index].decode("ascii", "replace").upper()}


def argument_ref(argument: bytes) -> int | None:
    """Return the entity id of an argument that is a plain ``#id`` reference."""
    argument = argument.strip()
    if len(argument) < 2 or argument[0] != _HASH:
        return None
    digits = argument[1:]
    return int(digits) if digits.isdigit() else None


def decode_step_string(argument: bytes) -> str:
    """Decode a raw STEP string argument into text for display purposes."""
    argument = argument.strip()
    if len(argument) >= 2 and argument[0] == _APOSTROPHE and argument[-1] == _APOSTROPHE:
        argument = argument[1:-1]
    argument = argument.replace(b"''", b"'")
    text = argument.decode("latin-1", errors="replace")
    return _decode_control_directives(text)


_X2_RE = re.compile(r"\\X2\\([0-9A-Fa-f]{4,})\\X0\\")
_X_RE = re.compile(r"\\X\\([0-9A-Fa-f]{2})")


def _decode_control_directives(text: str) -> str:
    """Resolve the ``\\X\\`` and ``\\X2\\`` escapes used by Part 21 strings."""
    if "\\" not in text:
        return text

    def expand_x2(match: re.Match[str]) -> str:
        digits = match.group(1)
        return "".join(
            chr(int(digits[i : i + 4], 16)) for i in range(0, len(digits) - 3, 4)
        )

    text = _X2_RE.sub(expand_x2, text)
    return _X_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def filter_reference_lists(record: bytes, keep: Container[int]) -> bytes | None:
    """Drop unwanted references from pure ``(#a,#b,...)`` aggregates.

    Used for entities such as ``PRODUCT_RELATED_PRODUCT_CATEGORY`` that collect
    references to many unrelated entities. Returns the rewritten record, the
    unchanged record when nothing had to be removed, or ``None`` when every
    aggregate became empty and the entity must be dropped.
    """
    start = payload_start(record)
    if start < 0:
        return record

    result = bytearray(record[:start])
    index = start
    end = len(record)
    changed = False
    emptied = False

    while index < end:
        char = record[index]
        if char == _APOSTROPHE:
            start = index
            index += 1
            while index < end:
                if record[index] == _APOSTROPHE:
                    if index + 1 < end and record[index + 1] == _APOSTROPHE:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            result += record[start:index]
            continue
        if char == _OPEN:
            arguments, after = parse_arguments(record, index)
            refs = [argument_ref(argument) for argument in arguments]
            if arguments and all(ref is not None for ref in refs):
                kept = [ref for ref in refs if ref in keep]
                if len(kept) != len(refs):
                    changed = True
                    if not kept:
                        emptied = True
                    result += b"(" + b",".join(b"#%d" % ref for ref in kept) + b")"
                    index = after
                    continue
                result += record[index:after]
                index = after
                continue
            # Not a pure reference list: descend so nested aggregates are seen.
            result.append(char)
            index += 1
            continue
        result.append(char)
        index += 1

    if emptied:
        return None
    return bytes(result) if changed else record
