"""Curses browser for the assembly structure with collapsible nodes.

The browser only reads the SQLite structure index; the STEP file itself is
never opened here. Children are fetched when a node is expanded, so even very
large assemblies stay responsive.
"""

from __future__ import annotations

import curses
import curses.ascii
import locale
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from . import model
from . import i18n as i18n_mod
from . import ui
from .util import safe_filename


_MAX_AUTO_EXPAND = 5000


def path_parts_for_item(item: "Item") -> tuple[str, ...]:
    """Folder segments from the assembly root down to the node's parent."""
    parts: list[str] = []
    node = item.parent
    while node is not None and not node.virtual:
        parts.append(safe_filename(node.name))
        node = node.parent
    return tuple(reversed(parts))


@dataclass
class Item:
    pd_id: int
    name: str
    depth: int
    usage_id: int | None = None
    designator: str = ""
    child_count: int = 0
    parent: "Item | None" = None
    children: "list[Item] | None" = None
    expanded: bool = False
    cycle: bool = False
    virtual: bool = False
    is_body: bool = False

    @property
    def key(self) -> tuple[int, ...]:
        keys: list[int] = []
        node: Item | None = self
        while node is not None:
            keys.append(node.usage_id if node.usage_id is not None else -node.pd_id - 1)
            node = node.parent
        return tuple(reversed(keys))

    def ancestors(self) -> Iterable["Item"]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class Tree:
    def __init__(self, connection: sqlite3.Connection, title: str) -> None:
        self.connection = connection
        self.root = Item(pd_id=-1, name=title, depth=0, virtual=True, expanded=True)
        roots = model.root_pds(connection)
        names = model.names_for_pds(connection, roots)
        counts = model.child_counts(connection, roots)
        self.root.children = [
            Item(
                pd_id=pd_id,
                name=names[pd_id],
                depth=1,
                child_count=counts.get(pd_id, 0),
                parent=self.root,
            )
            for pd_id in roots
        ]
        self.root.child_count = len(self.root.children)
        self.selected: dict[tuple[int, ...], Item] = {}
        self.rows: list[Item] = []
        self.refresh_rows()

    def load_children(self, item: Item) -> list[Item]:
        if item.is_body:
            item.children = []
            return item.children
        if item.children is None:
            ancestors = {node.pd_id for node in item.ancestors()}
            item.children = [
                Item(
                    pd_id=child.pd_id,
                    name=child.name,
                    depth=item.depth + 1,
                    usage_id=child.usage_id,
                    designator=child.designator,
                    child_count=child.child_count,
                    parent=item,
                    cycle=(
                        not child.is_body
                        and (child.pd_id in ancestors or child.pd_id == item.pd_id)
                    ),
                    is_body=child.is_body,
                )
                for child in model.children(self.connection, item.pd_id)
            ]
        return item.children

    def refresh_rows(self) -> None:
        rows: list[Item] = []
        stack = [self.root]
        while stack:
            item = stack.pop()
            rows.append(item)
            if item.expanded and item.children:
                stack.extend(reversed(item.children))
        self.rows = rows

    def expand(self, item: Item) -> None:
        if item.cycle or (item.child_count == 0 and not item.virtual):
            return
        self.load_children(item)
        item.expanded = True
        self.refresh_rows()

    def collapse(self, item: Item) -> None:
        item.expanded = False
        self.refresh_rows()

    def expand_recursive(self, item: Item) -> int:
        opened = 0
        stack = [item]
        while stack and opened < _MAX_AUTO_EXPAND:
            current = stack.pop()
            if current.cycle or (current.child_count == 0 and not current.virtual):
                continue
            self.load_children(current)
            current.expanded = True
            opened += 1
            stack.extend(current.children or [])
        self.refresh_rows()
        return opened

    def collapse_all(self) -> None:
        stack = list(self.root.children or [])
        while stack:
            current = stack.pop()
            current.expanded = False
            stack.extend(current.children or [])
        self.refresh_rows()

    def toggle_selection(self, item: Item) -> None:
        if item.virtual:
            return
        key = item.key
        if key in self.selected:
            del self.selected[key]
        else:
            self.selected[key] = item

    def is_selected(self, item: Item) -> bool:
        return item.key in self.selected

    def reveal(self, pd_id: int) -> int | None:
        """Expand the tree down to ``pd_id`` and return its row index."""
        path = model.path_to_root(self.connection, pd_id)
        item = self.root
        for step in path:
            self.load_children(item)
            item.expanded = True
            match = next((child for child in item.children or [] if child.pd_id == step), None)
            if match is None:
                break
            item = match
        self.refresh_rows()
        try:
            return self.rows.index(item)
        except ValueError:
            return None


class Browser:
    def __init__(
        self,
        tree: Tree,
        export: Callable[[object, list[model.Node]], bool],
        subtitle: str = "",
        language: str = "de",
    ) -> None:
        self.tree = tree
        self.export = export
        self.subtitle = subtitle
        self.i18n = i18n_mod.I18n(language)
        self.cursor = 0
        self.top = 0
        self.status = ""
        self.search_term = ""
        self.search_hits: list[int] = []
        self.search_position = 0

    # -- rendering ---------------------------------------------------------
    def draw(self, screen: "curses._CursesWindow") -> None:
        ui.THEME.init(screen)
        screen.erase()
        height, width = screen.getmaxyx()
        status_lines = 1 if self.status else 0
        body = max(height - 2 - status_lines, 1)
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + body:
            self.top = self.cursor - body + 1

        header = f" {self.i18n.t('tree_header')} - {self.subtitle}"
        ui.safe_add(screen, 0, 0, header, width - 1, ui.THEME.attr(ui.C_HEADER, curses.A_BOLD))

        for row in range(body):
            index = self.top + row
            if index >= len(self.tree.rows):
                break
            self._draw_item(screen, row + 1, width, index)

        marked = len(self.tree.selected)
        footer = (
            f" {marked} | {len(self.tree.rows)} | {self.i18n.t('tree_footer')}"
        )
        if self.status:
            ui.safe_add(
                screen,
                height - 2,
                0,
                " " + self.status,
                width - 1,
                ui.THEME.attr(ui.C_MUTED),
            )
        ui.safe_add(screen, height - 1, 0, footer, width - 1, ui.THEME.attr(ui.C_FOOTER))
        screen.noutrefresh()
        curses.doupdate()

    def _draw_item(self, screen, line: int, width: int, index: int) -> None:
        item = self.tree.rows[index]
        if item.virtual:
            marker = "  "
            handle = "▾" if item.expanded else "▸"
        else:
            marker = "[✓]" if self.tree.is_selected(item) else "[ ]"
            if item.cycle:
                handle = "↺"
            elif item.is_body:
                handle = "●"
            elif item.child_count:
                handle = "▾" if item.expanded else "▸"
            else:
                handle = "·"

        indent = "  " * item.depth
        suffix = ""
        if item.child_count and not item.is_body:
            suffix = f"  ({item.child_count})"
        if not item.virtual:
            suffix += f"  PD #{item.pd_id}"
        if item.designator and item.designator not in (item.name, ""):
            suffix += f"  <{item.designator}>"
        if item.is_body:
            suffix += f"  [{self.i18n.t('tree_body')}]"
        if item.cycle:
            suffix += f"  [{self.i18n.t('tree_cycle')}]"

        text = f"{marker} {indent}{handle} {item.name}{suffix}"
        if index == self.cursor:
            attribute = ui.THEME.attr(ui.C_SELECT, curses.A_BOLD)
        elif self.tree.is_selected(item):
            attribute = ui.THEME.attr(ui.C_OK, curses.A_BOLD)
        elif item.is_body:
            attribute = ui.THEME.attr(ui.C_MUTED)
        elif item.virtual:
            attribute = ui.THEME.attr(ui.C_TITLE, curses.A_BOLD)
        else:
            attribute = curses.A_NORMAL
        ui.safe_add(screen, line, 0, text, width - 1, attribute)

    # -- interaction -------------------------------------------------------
    def current(self) -> Item:
        return self.tree.rows[min(self.cursor, len(self.tree.rows) - 1)]

    def move(self, delta: int) -> None:
        self.cursor = max(0, min(self.cursor + delta, len(self.tree.rows) - 1))

    def prompt(self, screen, label: str) -> str:
        height, width = screen.getmaxyx()
        curses.echo()
        curses.curs_set(1)
        screen.addnstr(height - 1, 0, label.ljust(width - 1), width - 1)
        screen.move(height - 1, len(label))
        try:
            answer = screen.getstr(height - 1, len(label), 120).decode("utf-8", "replace")
        finally:
            curses.noecho()
            curses.curs_set(0)
        return answer.strip()

    def run(self, screen) -> None:
        curses.curs_set(0)
        screen.keypad(True)
        while True:
            self.draw(screen)
            key = screen.getch()
            if key == ord("q"):
                return
            if key == 27:
                # A lone escape only cancels; quitting stays on 'q' so that an
                # unrecognised escape sequence cannot close the browser.
                self.search_hits = []
                self.status = "search cleared"
                continue
            if key in (curses.KEY_DOWN, ord("j")):
                self.move(1)
            elif key in (curses.KEY_UP, ord("k")):
                self.move(-1)
            elif key == curses.KEY_NPAGE:
                self.move(screen.getmaxyx()[0] - 5)
            elif key == curses.KEY_PPAGE:
                self.move(-(screen.getmaxyx()[0] - 5))
            elif key == curses.KEY_HOME:
                self.cursor = 0
            elif key == curses.KEY_END:
                self.cursor = len(self.tree.rows) - 1
            elif key in (curses.KEY_RIGHT, ord("l"), curses.KEY_ENTER, 10, 13):
                item = self.current()
                if item.expanded:
                    self.move(1)
                else:
                    self.tree.expand(item)
            elif key in (curses.KEY_LEFT,):
                item = self.current()
                if item.expanded:
                    self.tree.collapse(item)
                elif item.parent is not None:
                    self.cursor = self.tree.rows.index(item.parent)
            elif key == ord(" "):
                item = self.current()
                self.tree.toggle_selection(item)
                self.status = self.i18n.t("tree_status_mark", n=len(self.tree.selected))
            elif key == ord("a"):
                opened = self.tree.expand_recursive(self.current())
                self.status = f"expanded {opened}"
            elif key == ord("c"):
                self.tree.collapse_all()
                self.cursor = 0
            elif key == ord("x"):
                self.tree.selected.clear()
                self.status = self.i18n.t("tree_status_clear")
            elif key == ord("/"):
                self._search(screen)
            elif key == ord("n"):
                self._next_hit()
            elif key == ord("h"):
                self._show_help(screen)
            elif key == ord("i"):
                self._show_info(screen)
            elif key == ord("e"):
                if not self.tree.selected:
                    self.status = self.i18n.t("tree_status_export_empty")
                    continue
                self._export(screen)

    def _show_help(self, screen) -> None:
        ui.show_lines(
            screen,
            self.i18n.t("tree_help_title"),
            self.i18n.t("tree_help").splitlines(),
        )

    def _show_info(self, screen) -> None:
        item = self.current()
        if item.virtual:
            lines = [
                self.i18n.t("tree_info_file", name=item.name),
                self.i18n.t(
                    "tree_info_roots",
                    n=item.child_count or len(item.children or []),
                ),
            ]
            ui.show_lines(screen, self.i18n.t("tree_info_title"), lines)
            return

        info = model.node_info(self.tree.connection, item.pd_id, item.usage_id)
        yes = self.i18n.t("yes")
        no = self.i18n.t("no")
        path_names = " / ".join(
            ancestor.name for ancestor in reversed(list(item.ancestors())) if not ancestor.virtual
        )
        lines = [
            self.i18n.t("tree_info_name", value=info["name"]),
            self.i18n.t("tree_info_pd", value=info["pd_id"]),
            self.i18n.t("tree_info_product", value=info["product_id"] or "-"),
            self.i18n.t("tree_info_ident", value=info["ident"] or "-"),
            self.i18n.t("tree_info_formation", value=info["formation_id"] or "-"),
            self.i18n.t(
                "tree_info_children",
                value=item.child_count,
                usages=info["child_usages"],
            ),
            self.i18n.t(
                "tree_info_shape",
                value=yes if info["has_shape"] else no,
                links=info["shape_links"],
            ),
        ]
        if item.is_body:
            lines.append(self.i18n.t("tree_info_body"))
        if item.cycle:
            lines.append(self.i18n.t("tree_info_cycle"))
        if path_names:
            lines.append(self.i18n.t("tree_info_path", value=path_names))
        usage = info.get("usage")
        if usage:
            parent_name = model.name_for_pd(self.tree.connection, usage["parent_pd"])
            lines.extend(
                [
                    "",
                    self.i18n.t("tree_info_usage_header"),
                    self.i18n.t("tree_info_usage_id", value=usage["usage_id"]),
                    self.i18n.t(
                        "tree_info_usage_parent",
                        value=f"{parent_name}  (PD #{usage['parent_pd']})",
                    ),
                    self.i18n.t("tree_info_usage_type", value=usage["usage_type"] or "-"),
                    self.i18n.t(
                        "tree_info_designator",
                        value=usage["designator"] or "-",
                    ),
                ]
            )
        elif item.designator:
            lines.append(self.i18n.t("tree_info_designator", value=item.designator))
        ui.show_lines(screen, self.i18n.t("tree_info_title"), lines)

    def _search(self, screen) -> None:
        term = self.prompt(screen, "search product: ")
        if not term:
            return
        self.search_term = term
        matches = model.search(self.tree.connection, term, limit=500)
        self.search_hits = [node.pd_id for node in matches]
        self.search_position = -1
        if not self.search_hits:
            self.status = f"no product matches {term!r}"
            return
        self.status = f"{len(self.search_hits)} match(es) for {term!r} (n for next)"
        self._next_hit()

    def _next_hit(self) -> None:
        if not self.search_hits:
            self.status = "no active search"
            return
        self.search_position = (self.search_position + 1) % len(self.search_hits)
        pd_id = self.search_hits[self.search_position]
        index = self.tree.reveal(pd_id)
        if index is None:
            self.status = f"PD #{pd_id} is not reachable from a root node"
            return
        self.cursor = index
        self.status = (
            f"match {self.search_position + 1}/{len(self.search_hits)}: "
            f"{self.tree.rows[index].name}"
        )

    def _export(self, screen) -> None:
        nodes = [
            model.Node(
                pd_id=item.pd_id,
                name=item.name,
                usage_id=item.usage_id,
                designator=item.designator,
                child_count=item.child_count,
                path_parts=path_parts_for_item(item),
            )
            for item in self.tree.selected.values()
        ]
        try:
            self.export(screen, nodes)
        except SystemExit as error:
            ui.show_lines(screen, self.i18n.t("error"), [str(error)])
        except Exception as error:  # noqa: BLE001 - keep the browser alive
            ui.show_lines(screen, self.i18n.t("error"), [str(error)])
        self.status = self.i18n.t("tree_status_done")


def browse(
    connection: sqlite3.Connection,
    title: str,
    export: Callable[[object, list[model.Node]], bool],
    subtitle: str = "",
    language: str = "de",
) -> None:
    locale.setlocale(locale.LC_ALL, "")
    tree = Tree(connection, title)
    if not tree.root.children:
        raise SystemExit("The index contains no root product definition to browse.")
    browser = Browser(tree, export, subtitle or title, language=language)
    curses.wrapper(browser.run)
