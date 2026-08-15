"""Read-only queries over the indexed assembly structure."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from . import storage
from .scan import verify_fingerprint


@dataclass
class Node:
    """One occurrence of a product definition inside the assembly tree."""

    pd_id: int
    name: str
    usage_id: int | None = None
    designator: str = ""
    child_count: int = 0
    cycle: bool = False
    # Kisters / CAD viewers show a leaf part's solid as a same-named child node.
    # That child is not a separate PRODUCT_DEFINITION; it is display-only.
    is_body: bool = False
    path: tuple[int, ...] = field(default_factory=tuple)
    # Folder segments from assembly root to parent (for hierarchical export).
    path_parts: tuple[str, ...] = field(default_factory=tuple)

    @property
    def label(self) -> str:
        text = self.name
        if self.is_body:
            return text
        if self.designator and self.designator != self.name:
            text = f"{text}  <{self.designator}>"
        return text


def open_structure(source: Path, work_dir: Path, require_complete: bool = True) -> sqlite3.Connection:
    try:
        connection = storage.connect(work_dir)
    except FileNotFoundError as error:
        raise SystemExit(
            f"No structure index found in {work_dir}. Run the 'index' command first."
        ) from error
    meta = storage.read_meta(connection)
    if not meta:
        raise SystemExit(f"The index in {work_dir} is empty. Run the 'index' command first.")
    verify_fingerprint(connection, source)
    if require_complete and meta.get("scan_state") != "complete":
        raise SystemExit(
            "The index is incomplete. Re-run the 'index' command to resume the scan."
        )
    return connection


def has_offsets(work_dir: Path) -> bool:
    path = storage.offsets_path(work_dir)
    return path.exists() and path.stat().st_size > 8


def counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "products",
        "formations",
        "product_definitions",
        "usages",
        "definition_shapes",
        "shape_representations",
        "context_shapes",
    )
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }


def name_for_pd(connection: sqlite3.Connection, pd_id: int) -> str:
    row = connection.execute(
        """
        SELECT p.name FROM product_definitions pd
        JOIN formations f ON f.formation_id = pd.formation_id
        JOIN products p   ON p.product_id  = f.product_id
        WHERE pd.pd_id = ?
        """,
        (pd_id,),
    ).fetchone()
    return row[0] if row else f"<unnamed PD #{pd_id}>"


def node_info(connection: sqlite3.Connection, pd_id: int, usage_id: int | None = None) -> dict:
    """Indexed facts about a product definition (and optional usage occurrence)."""
    row = connection.execute(
        """
        SELECT pd.pd_id, pd.formation_id, f.product_id, p.ident, p.name
        FROM product_definitions pd
        JOIN formations f ON f.formation_id = pd.formation_id
        JOIN products p   ON p.product_id  = f.product_id
        WHERE pd.pd_id = ?
        """,
        (pd_id,),
    ).fetchone()
    info: dict = {
        "pd_id": pd_id,
        "found": row is not None,
        "formation_id": None,
        "product_id": None,
        "ident": "",
        "name": f"<unnamed PD #{pd_id}>",
        "child_usages": 0,
        "has_shape": False,
        "shape_links": 0,
        "usage": None,
    }
    if row:
        info.update(
            {
                "pd_id": row[0],
                "formation_id": row[1],
                "product_id": row[2],
                "ident": row[3] or "",
                "name": row[4] or info["name"],
            }
        )
    info["child_usages"] = connection.execute(
        "SELECT COUNT(*) FROM usages WHERE parent_pd=?", (pd_id,)
    ).fetchone()[0]
    info["shape_links"] = connection.execute(
        "SELECT COUNT(*) FROM definition_shapes WHERE definition_id=?", (pd_id,)
    ).fetchone()[0]
    info["has_shape"] = info["shape_links"] > 0
    if usage_id is not None:
        usage = connection.execute(
            """
            SELECT usage_id, parent_pd, child_pd, usage_type, designator, parse_mode
            FROM usages WHERE usage_id=?
            """,
            (usage_id,),
        ).fetchone()
        if usage:
            info["usage"] = {
                "usage_id": usage[0],
                "parent_pd": usage[1],
                "child_pd": usage[2],
                "usage_type": usage[3],
                "designator": usage[4] or "",
                "parse_mode": usage[5] or "",
            }
    return info


def names_for_pds(connection: sqlite3.Connection, pd_ids: list[int]) -> dict[int, str]:
    if not pd_ids:
        return {}
    placeholders = ",".join("?" * len(pd_ids))
    rows = connection.execute(
        f"""
        SELECT pd.pd_id, p.name FROM product_definitions pd
        JOIN formations f ON f.formation_id = pd.formation_id
        JOIN products p   ON p.product_id  = f.product_id
        WHERE pd.pd_id IN ({placeholders})
        """,
        pd_ids,
    ).fetchall()
    mapping = {pd_id: f"<unnamed PD #{pd_id}>" for pd_id in pd_ids}
    mapping.update(dict(rows))
    return mapping


def root_pds(connection: sqlite3.Connection) -> list[int]:
    """Product definitions that are never used as a component."""
    return [
        row[0]
        for row in connection.execute(
            """
            SELECT pd.pd_id FROM product_definitions pd
            WHERE NOT EXISTS (SELECT 1 FROM usages u WHERE u.child_pd = pd.pd_id)
            ORDER BY pd.pd_id
            """
        )
    ]


def _has_shape(connection: sqlite3.Connection, pd_id: int) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM definition_shapes WHERE definition_id=? LIMIT 1", (pd_id,)
        ).fetchone()
        is not None
    )


def _display_child_count(connection: sqlite3.Connection, pd_id: int, usage_count: int) -> int:
    """How many children the tree should show for this product definition.

    Assembly nodes use the real usage count. Leaf parts with geometry get one
    extra display child (the solid), matching Kisters / typical CAD browsers.
    """
    if usage_count:
        return usage_count
    return 1 if _has_shape(connection, pd_id) else 0


def children(connection: sqlite3.Connection, pd_id: int) -> list[Node]:
    rows = connection.execute(
        "SELECT usage_id, child_pd, designator FROM usages WHERE parent_pd=? ORDER BY usage_id",
        (pd_id,),
    ).fetchall()
    if rows:
        names = names_for_pds(connection, [row[1] for row in rows])
        counts_by_pd = child_counts(connection, [row[1] for row in rows])
        return [
            Node(
                pd_id=child_pd,
                name=names[child_pd],
                usage_id=usage_id,
                designator=designator,
                child_count=counts_by_pd.get(child_pd, 0),
            )
            for usage_id, child_pd, designator in rows
        ]

    # Leaf part: CAD viewers still show the solid under the occurrence.
    if _has_shape(connection, pd_id):
        return [
            Node(
                pd_id=pd_id,
                name=name_for_pd(connection, pd_id),
                child_count=0,
                is_body=True,
            )
        ]
    return []


def child_counts(connection: sqlite3.Connection, pd_ids: list[int]) -> dict[int, int]:
    if not pd_ids:
        return {}
    unique = sorted(set(pd_ids))
    placeholders = ",".join("?" * len(unique))
    usage_counts = dict(
        connection.execute(
            f"SELECT parent_pd, COUNT(*) FROM usages WHERE parent_pd IN ({placeholders})"
            " GROUP BY parent_pd",
            unique,
        )
    )
    shaped = {
        row[0]
        for row in connection.execute(
            f"SELECT DISTINCT definition_id FROM definition_shapes"
            f" WHERE definition_id IN ({placeholders})",
            unique,
        )
    }
    return {
        pd_id: usage_counts[pd_id]
        if pd_id in usage_counts
        else (1 if pd_id in shaped else 0)
        for pd_id in unique
    }


def resolve_selector(connection: sqlite3.Connection, selector: str) -> list[Node]:
    """Resolve ``#id``, ``pd:id``, ``product:id`` or a product name to nodes.

    A bare ``#id`` may address either a PRODUCT_DEFINITION or a PRODUCT; both
    are accepted so ids copied from a STEP file can be used directly.
    """
    selector = selector.strip()
    pd_ids: list[int] = []

    if selector.lower().startswith("pd:"):
        pd_ids = [int(selector[3:].lstrip("#"))]
    elif selector.lower().startswith("product:"):
        pd_ids = _pds_for_product(connection, int(selector[8:].lstrip("#")))
    elif selector.startswith("#") and selector[1:].isdigit():
        entity = int(selector[1:])
        if connection.execute(
            "SELECT 1 FROM product_definitions WHERE pd_id=?", (entity,)
        ).fetchone():
            pd_ids = [entity]
        else:
            pd_ids = _pds_for_product(connection, entity)
    else:
        pd_ids = [
            row[0]
            for row in connection.execute(
                """
                SELECT pd.pd_id FROM products p
                JOIN formations f          ON f.product_id   = p.product_id
                JOIN product_definitions pd ON pd.formation_id = f.formation_id
                WHERE p.name = ? COLLATE NOCASE
                ORDER BY pd.pd_id
                """,
                (selector,),
            )
        ]

    if not pd_ids:
        raise SystemExit(_not_found_message(connection, selector))

    counts_by_pd = child_counts(connection, pd_ids)
    names = names_for_pds(connection, pd_ids)
    return [
        Node(pd_id=pd_id, name=names[pd_id], child_count=counts_by_pd.get(pd_id, 0))
        for pd_id in pd_ids
    ]


def _pds_for_product(connection: sqlite3.Connection, product_id: int) -> list[int]:
    return [
        row[0]
        for row in connection.execute(
            """
            SELECT pd.pd_id FROM product_definitions pd
            JOIN formations f ON f.formation_id = pd.formation_id
            WHERE f.product_id = ?
            ORDER BY pd.pd_id
            """,
            (product_id,),
        )
    ]


def _not_found_message(connection: sqlite3.Connection, selector: str) -> str:
    similar = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT name FROM products WHERE name LIKE ? ORDER BY name LIMIT 20",
            (f"%{selector.lstrip('#')}%",),
        )
    ]
    message = f"No product matches {selector!r}."
    if similar:
        message += "\nSimilar product names:\n  " + "\n  ".join(similar)
    return message


def search(connection: sqlite3.Connection, text: str, limit: int = 200) -> list[Node]:
    rows = connection.execute(
        """
        SELECT pd.pd_id, p.name FROM products p
        JOIN formations f           ON f.product_id   = p.product_id
        JOIN product_definitions pd ON pd.formation_id = f.formation_id
        WHERE p.name LIKE ? COLLATE NOCASE
        ORDER BY p.name LIMIT ?
        """,
        (f"%{text}%", limit),
    ).fetchall()
    counts_by_pd = child_counts(connection, [row[0] for row in rows])
    return [
        Node(pd_id=pd_id, name=name, child_count=counts_by_pd.get(pd_id, 0))
        for pd_id, name in rows
    ]


def subtree(connection: sqlite3.Connection, root_pd: int) -> tuple[set[int], set[int]]:
    """Return every product definition and usage below ``root_pd`` (inclusive)."""
    product_definitions: set[int] = set()
    usages: set[int] = set()
    frontier = [root_pd]
    while frontier:
        batch = frontier
        frontier = []
        pending = [pd_id for pd_id in batch if pd_id not in product_definitions]
        product_definitions.update(pending)
        if not pending:
            continue
        for start in range(0, len(pending), 500):
            window = pending[start : start + 500]
            placeholders = ",".join("?" * len(window))
            for usage_id, child_pd in connection.execute(
                f"SELECT usage_id, child_pd FROM usages WHERE parent_pd IN ({placeholders})",
                window,
            ):
                usages.add(usage_id)
                if child_pd not in product_definitions:
                    frontier.append(child_pd)
    return product_definitions, usages


def path_to_root(connection: sqlite3.Connection, pd_id: int, limit: int = 200) -> list[int]:
    """Walk upwards through the usages and return ``[root, ..., pd_id]``."""
    path = [pd_id]
    seen = {pd_id}
    current = pd_id
    for _ in range(limit):
        row = connection.execute(
            "SELECT parent_pd FROM usages WHERE child_pd=? ORDER BY usage_id LIMIT 1",
            (current,),
        ).fetchone()
        if row is None or row[0] in seen:
            break
        current = row[0]
        seen.add(current)
        path.append(current)
    path.reverse()
    return path


def iter_tree(
    connection: sqlite3.Connection,
    root_pd: int,
    max_depth: int | None = None,
):
    """Depth-first walk yielding ``(depth, Node)``; repeated cycles are cut."""
    root_name = name_for_pd(connection, root_pd)
    root_children = child_counts(connection, [root_pd]).get(root_pd, 0)
    stack: list[tuple[int, Node, bool]] = [
        (0, Node(pd_id=root_pd, name=root_name, child_count=root_children, path=(root_pd,)), False)
    ]
    active: set[int] = set()
    while stack:
        depth, node, leaving = stack.pop()
        if leaving:
            active.discard(node.pd_id)
            continue
        node.cycle = (not node.is_body) and (node.pd_id in active)
        yield depth, node
        if node.cycle or node.is_body or (max_depth is not None and depth >= max_depth):
            continue
        active.add(node.pd_id)
        stack.append((depth, node, True))
        for child in reversed(children(connection, node.pd_id)):
            child.path = node.path + (child.pd_id,)
            stack.append((depth + 1, child, False))
