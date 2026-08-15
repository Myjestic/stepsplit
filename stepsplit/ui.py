"""Shared curses widgets: colorful menus in the structure-browser style."""

from __future__ import annotations

import curses
import locale
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from . import i18n as i18n_mod
from .util import is_step_file


# Color pair ids
C_HEADER = 1
C_FOOTER = 2
C_SELECT = 3
C_ACCENT = 4
C_OK = 5
C_MUTED = 6
C_TITLE = 7
C_WARN = 8


@dataclass
class Theme:
    color: bool = True

    def init(self, screen) -> None:
        curses.curs_set(0)
        screen.keypad(True)
        if not self.color or not curses.has_colors():
            self.color = False
            return
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass
        curses.init_pair(C_HEADER, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(C_FOOTER, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(C_SELECT, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(C_ACCENT, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_OK, curses.COLOR_GREEN, -1)
        curses.init_pair(C_MUTED, curses.COLOR_WHITE, -1)
        curses.init_pair(C_TITLE, curses.COLOR_CYAN, -1)
        curses.init_pair(C_WARN, curses.COLOR_RED, -1)

    def attr(self, pair: int, *extra: int) -> int:
        value = 0
        for item in extra:
            value |= item
        if self.color:
            return curses.color_pair(pair) | value
        if pair in {C_HEADER, C_FOOTER, C_SELECT}:
            return curses.A_REVERSE | value
        if pair in {C_ACCENT, C_TITLE}:
            return curses.A_BOLD | value
        if pair == C_MUTED:
            return curses.A_DIM | value
        return value


THEME = Theme()


def ensure_locale() -> None:
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass


def safe_add(screen, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
    try:
        screen.addnstr(y, x, text.ljust(max(width, 1)), max(width, 1), attr)
    except curses.error:
        pass


def _put(screen, y: int, x: int, text: str, attr: int = 0) -> None:
    """Write ``text`` at (y, x) without padding beyond the string itself."""
    if y < 0 or x < 0 or not text:
        return
    try:
        height, width = screen.getmaxyx()
        if y >= height or x >= width:
            return
        room = width - x
        if room <= 0:
            return
        screen.addnstr(y, x, text, min(len(text), room), attr)
    except curses.error:
        pass


@dataclass
class MenuItem:
    key: str
    label: str
    hint: str = ""
    enabled: bool = True
    separator: bool = False


@dataclass
class HeaderPanel:
    """Compact status card under the title bar."""

    eyebrow: str = ""
    # Each row is (label, value) or (label, value, value_color_pair).
    rows: Sequence[tuple[str, str] | tuple[str, str, int]] = ()
    note: str = ""


def _draw_header_panel(screen, start_line: int, width: int, panel: HeaderPanel) -> int:
    """Draw a framed status card; return the next free line index.

    Borders always use the title color so they stay consistent even when the
    row content uses accent / warn / ok attributes.
    """
    line = start_line
    # Leave one column free at the right edge (curses often rejects writes there).
    box_left = 2
    box_width = width - box_left - 1
    if box_width < 24:
        return line
    inner = box_width - 4  # "│ " + content + " │"
    border = THEME.attr(C_TITLE)

    def row_frame(content: str = "", content_attr: int = 0) -> None:
        nonlocal line
        clipped = content[:inner].ljust(inner)
        _put(screen, line, box_left, "│ ", border)
        _put(screen, line, box_left + 2, clipped, content_attr)
        _put(screen, line, box_left + 2 + inner, " │", border)
        line += 1

    top = "┌" + "─" * (inner + 2) + "┐"
    bot = "└" + "─" * (inner + 2) + "┘"
    _put(screen, line, box_left, top, border)
    line += 1

    if panel.eyebrow:
        row_frame(panel.eyebrow, THEME.attr(C_ACCENT, curses.A_BOLD))
        row_frame("", border)

    label_width = min(
        14,
        max((len(row[0]) for row in panel.rows), default=6),
    )
    for row in panel.rows:
        label = row[0]
        value = row[1]
        value_pair = row[2] if len(row) > 2 else C_MUTED
        label_text = label[:label_width].ljust(label_width)
        room = max(inner - label_width - 3, 8)
        value_text = value if len(value) <= room else "…" + value[-(room - 1) :]
        # Draw the full content line first (muted value color), then recolor label.
        row_frame(f"{label_text} : {value_text}", THEME.attr(value_pair))
        _put(
            screen,
            line - 1,
            box_left + 2,
            label_text,
            THEME.attr(C_ACCENT, curses.A_BOLD),
        )

    if panel.note:
        row_frame("", border)
        row_frame(panel.note, THEME.attr(C_OK))

    _put(screen, line, box_left, bot, border)
    line += 1
    return line


def _wrap_words(text: str, width: int) -> list[str]:
    """Wrap ``text`` to ``width`` columns without breaking words when possible."""
    if width < 1:
        return [""]
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_side_hint(
    screen,
    top: int,
    left: int,
    box_width: int,
    height: int,
    text: str,
) -> None:
    """Draw a framed help box to the right of the menu."""
    if box_width < 8 or height < 3:
        return
    inner = box_width - 4
    raw_lines: list[str] = []
    if text.strip():
        for paragraph in text.splitlines() or [text]:
            raw_lines.extend(_wrap_words(paragraph, inner))
    max_rows = height - 2
    visible = raw_lines[:max_rows]
    while len(visible) < max_rows:
        visible.append("")

    border = THEME.attr(C_TITLE)
    content_attr = THEME.attr(C_MUTED)
    top_border = "┌" + "─" * (box_width - 2) + "┐"
    bot_border = "└" + "─" * (box_width - 2) + "┘"
    _put(screen, top, left, top_border, border)
    for row, line in enumerate(visible):
        y = top + 1 + row
        _put(screen, y, left, "│ ", border)
        _put(screen, y, left + 2, line.ljust(inner)[:inner], content_attr)
        _put(screen, y, left + 2 + inner, " │", border)
    _put(screen, top + 1 + max_rows, left, bot_border, border)


def list_menu(
    screen,
    title: str,
    items: Sequence[MenuItem],
    status: str = "",
    subtitle_lines: Sequence[str] = (),
    panel: HeaderPanel | None = None,
    cursor: int = 0,
    hint_mode: str = "inline",
) -> str | None:
    """Arrow-key menu. Returns the selected item key, or ``None`` if cancelled.

    ``hint_mode``:
    - ``inline``: append hint after the label with a middle dot
    - ``aligned``: ``label : value`` with values left-aligned in a column
    - ``side``: show only the label; put the current hint in a box on the right
    """
    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    enabled = [i for i, item in enumerate(items) if item.enabled and not item.separator]
    if not enabled:
        return None
    if cursor not in enabled:
        cursor = enabled[0]

    label_width = max((len(item.label) for item in items if not item.separator), default=0)

    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))

        line = 2
        if panel is not None:
            line = _draw_header_panel(screen, line, width, panel)
        else:
            for text in subtitle_lines:
                safe_add(screen, line, 2, text, width - 3, THEME.attr(C_MUTED))
                line += 1
            if subtitle_lines:
                line += 1

        body_top = line
        body_height = max(height - body_top - 2, 1)
        first = 0
        if cursor - first >= body_height:
            first = cursor - body_height + 1

        side_box_width = 0
        menu_width = width - 2
        if hint_mode == "side" and width >= 48:
            side_box_width = min(42, max(26, width // 2 - 4))
            menu_width = max(18, width - side_box_width - 5)

        for row in range(body_height):
            index = first + row
            if index >= len(items):
                break
            item = items[index]
            if item.separator:
                safe_add(screen, body_top + row, 1, "", menu_width)
                continue
            marker = "▸" if index == cursor else " "
            if hint_mode == "aligned" and item.hint:
                label = f"{item.label.ljust(label_width)} : {item.hint}"
            elif hint_mode == "inline" and item.hint:
                label = f"{item.label}  ·  {item.hint}"
            else:
                label = item.label
            text = f" {marker} {label}"
            if index == cursor and item.enabled:
                attr = THEME.attr(C_SELECT, curses.A_BOLD)
            elif not item.enabled:
                attr = THEME.attr(C_MUTED, curses.A_DIM)
            else:
                attr = curses.A_NORMAL
            safe_add(screen, body_top + row, 1, text, menu_width, attr)

        if hint_mode == "side" and side_box_width:
            hint = items[cursor].hint if not items[cursor].separator else ""
            if hint.strip():
                _draw_side_hint(
                    screen,
                    body_top,
                    width - side_box_width - 1,
                    side_box_width,
                    body_height,
                    hint,
                )

        footer = status or tr("nav_footer")
        safe_add(screen, height - 1, 0, f" {footer}", width - 1, THEME.attr(C_FOOTER))
        screen.refresh()

        key = screen.getch()
        if key in (ord("q"), 27):
            return None
        if key in (curses.KEY_UP, ord("k")):
            position = enabled.index(cursor)
            cursor = enabled[(position - 1) % len(enabled)]
        elif key in (curses.KEY_DOWN, ord("j")):
            position = enabled.index(cursor)
            cursor = enabled[(position + 1) % len(enabled)]
        elif key == curses.KEY_HOME:
            cursor = enabled[0]
        elif key == curses.KEY_END:
            cursor = enabled[-1]
        elif key in (curses.KEY_ENTER, 10, 13):
            if items[cursor].enabled and not items[cursor].separator:
                return items[cursor].key


def _path_matches(value: str, *, step_files_only: bool = False) -> list[str]:
    """Return filesystem matches for path-style tab completion."""
    text = value
    if text in {"", "."}:
        text = "./"
    if text == "~":
        return ["~/"]

    expanded = os.path.expanduser(text)

    if text.endswith(("/", os.sep)):
        directory = expanded.rstrip("/\\") or "/"
        incomplete = ""
        display_prefix = text
    else:
        directory = os.path.dirname(expanded)
        if directory == "":
            directory = "."
        incomplete = os.path.basename(expanded)
        slash = text.rfind("/")
        display_prefix = text[: slash + 1] if slash >= 0 else ""

    try:
        names = os.listdir(directory)
    except OSError:
        return []

    incomplete_lower = incomplete.lower()
    matches: list[str] = []
    for name in sorted(names, key=str.lower):
        if name.startswith("."):
            continue
        if incomplete and not name.lower().startswith(incomplete_lower):
            continue
        full = os.path.join(directory, name)
        display = display_prefix + name
        if os.path.isdir(full):
            display += "/"
            matches.append(display)
        elif not step_files_only or is_step_file(Path(full)):
            matches.append(display)
    return matches


def _common_prefix(items: Sequence[str]) -> str:
    if not items:
        return ""
    prefix = items[0]
    for item in items[1:]:
        while not item.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix


def _wrap_chars(text: str, width: int) -> list[str]:
    """Hard-wrap ``text`` by character columns (for paths without spaces)."""
    if width < 1:
        return [text]
    if not text:
        return [""]
    return [text[index : index + width] for index in range(0, len(text), width)]


def prompt_text(
    screen,
    title: str,
    label: str,
    default: str = "",
    *,
    path_complete: bool = False,
    step_files_only: bool = False,
) -> str | None:
    """Text prompt with wrapped input. Returns ``None`` if cancelled with Esc."""
    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    curses.curs_set(1)
    value = default
    listings: list[str] = []
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))
        safe_add(screen, 2, 2, label, width - 3, THEME.attr(C_TITLE))

        line_width = max(width - 4, 8)
        display = "❯ " + value
        wrapped = _wrap_chars(display, line_width)
        input_top = 4
        for row, chunk in enumerate(wrapped):
            safe_add(
                screen,
                input_top + row,
                2,
                chunk,
                line_width,
                THEME.attr(C_ACCENT, curses.A_BOLD),
            )

        list_top = input_top + len(wrapped) + 1
        if listings:
            max_rows = max(height - list_top - 2, 0)
            shown = listings[:max_rows]
            if shown == [""]:
                safe_add(
                    screen,
                    list_top,
                    4,
                    tr("prompt_no_matches"),
                    width - 5,
                    THEME.attr(C_MUTED),
                )
            else:
                for row, item in enumerate(shown):
                    safe_add(
                        screen,
                        list_top + row,
                        4,
                        item,
                        width - 5,
                        THEME.attr(C_MUTED),
                    )
                if len(listings) > max_rows > 0:
                    safe_add(
                        screen,
                        min(list_top + max_rows, height - 2),
                        4,
                        f"… +{len(listings) - max_rows}",
                        width - 5,
                        THEME.attr(C_MUTED),
                    )

        footer = tr("prompt_footer_path") if path_complete else tr("prompt_footer")
        safe_add(
            screen,
            height - 1,
            0,
            f" {footer}",
            width - 1,
            THEME.attr(C_FOOTER),
        )
        cursor_index = len(display)
        cursor_row = input_top + (cursor_index // line_width)
        cursor_col = 2 + (cursor_index % line_width)
        # When the cursor sits exactly on a wrap boundary, place it on the next line.
        if cursor_index > 0 and cursor_index % line_width == 0:
            cursor_row = input_top + (cursor_index // line_width)
            cursor_col = 2
        try:
            screen.move(min(cursor_row, height - 2), min(cursor_col, width - 2))
        except curses.error:
            pass
        screen.refresh()

        key = screen.getch()
        if key == 27:
            curses.curs_set(0)
            return None
        if key in (curses.KEY_ENTER, 10, 13):
            curses.curs_set(0)
            return value
        if key in (curses.KEY_BACKSPACE, 127, 8, curses.KEY_DC):
            value = value[:-1]
            listings = []
        elif path_complete and key == 9:  # Tab
            matches = _path_matches(value, step_files_only=step_files_only)
            if not matches:
                listings = [""]
                continue
            common = _common_prefix(matches)
            if common and common != value:
                value = common
                listings = []
                continue
            # Already at the longest common prefix → list matches.
            listings = matches
        elif 32 <= key < 127:
            value += chr(key)
            listings = []


def show_lines(
    screen,
    title: str,
    lines: Sequence[str],
    footer: str | None = None,
) -> None:
    """Scrollable read-only text page."""
    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    footer = footer or tr("back_footer")
    top = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))
        body = max(height - 2, 1)
        for row in range(body):
            index = top + row
            if index >= len(lines):
                break
            safe_add(screen, row + 1, 1, lines[index], width - 2)
        safe_add(screen, height - 1, 0, f" {footer}", width - 1, THEME.attr(C_FOOTER))
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), 27, curses.KEY_ENTER, 10, 13):
            return
        if key in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            top = min(max(0, len(lines) - body), top + 1)
        elif key == curses.KEY_PPAGE:
            top = max(0, top - body)
        elif key == curses.KEY_NPAGE:
            top = min(max(0, len(lines) - body), top + body)


def show_status(
    screen,
    title: str,
    panel: HeaderPanel,
    findings: Sequence[tuple[str, str]],
    result_ok: bool | None,
    result_text: str,
    footer: str | None = None,
) -> None:
    """Status page: framed info card + coloured check findings."""
    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    footer = footer or tr("back_footer")
    badge = {
        "error": (tr("sev_fail"), C_WARN),
        "warning": (tr("sev_warn"), C_ACCENT),
        "info": (tr("sev_ok"), C_OK),
    }
    badge_width = max(len(label) for label, _ in badge.values())
    content_lines: list[tuple[str, int]] = []
    if findings:
        content_lines.append((tr("status_section_check"), THEME.attr(C_TITLE, curses.A_BOLD)))
        content_lines.append(("", 0))
        for severity, message in findings:
            label, colour = badge.get(severity, (severity, C_MUTED))
            content_lines.append(
                (f"[{label.ljust(badge_width)}]  {message}", THEME.attr(colour))
            )
        if result_text:
            content_lines.append(("", 0))
            result_attr = THEME.attr(C_OK if result_ok else C_WARN, curses.A_BOLD)
            content_lines.append((result_text, result_attr))
    else:
        content_lines.append((tr("status_no_check"), THEME.attr(C_MUTED)))

    top = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))
        line = _draw_header_panel(screen, 1, width, panel)
        body = max(height - line - 1, 1)
        for row in range(body):
            index = top + row
            if index >= len(content_lines):
                break
            text, attr = content_lines[index]
            safe_add(screen, line + row, 2, text, width - 3, attr)
        safe_add(screen, height - 1, 0, f" {footer}", width - 1, THEME.attr(C_FOOTER))
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), 27, curses.KEY_ENTER, 10, 13):
            return
        if key in (curses.KEY_UP, ord("k")):
            top = max(0, top - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            top = min(max(0, len(content_lines) - body), top + 1)
        elif key == curses.KEY_PPAGE:
            top = max(0, top - body)
        elif key == curses.KEY_NPAGE:
            top = min(max(0, len(content_lines) - body), top + body)


def confirm(screen, title: str, question: str, default_no: bool = True) -> bool:
    tr = i18n_mod.get_i18n().t
    items = [
        MenuItem("yes", tr("yes"), tr("yes_hint")),
        MenuItem("no", tr("no"), tr("no_hint")),
    ]
    choice = list_menu(
        screen,
        title,
        items,
        subtitle_lines=question.splitlines(),
        cursor=1 if default_no else 0,
        status=tr("confirm_footer"),
    )
    return choice == "yes"


def _progress_bar(percent: float, width: int) -> str:
    width = max(width, 8)
    filled = int(round(min(max(percent, 0.0), 100.0) / 100.0 * width))
    return "█" * filled + "░" * (width - filled)


def run_with_progress(
    screen,
    title: str,
    subtitle: str,
    work: Callable[[Callable[[dict[str, object]], None]], None],
    *,
    finish: Callable[[], tuple[bool, str, str]] | None = None,
    footer: str | None = None,
) -> bool:
    """Show an in-menu progress card, keep it at the end, wait for Enter.

    ``finish`` may return ``(ok, headline, detail)`` shown under the finished bar.
    """
    from .util import format_bytes, format_duration

    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    live_footer = footer or tr("progress_footer")
    state: dict[str, object] = {
        "label": title,
        "percent": 0.0,
        "position": 0,
        "total": 1,
        "rate": 0.0,
        "elapsed": 0.0,
        "eta": 0.0,
        "detail": "",
    }
    done = False
    done_ok = True
    done_headline = ""

    def draw() -> None:
        screen.erase()
        height, width = screen.getmaxyx()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))

        inner = max(width - 8, 20)
        line = 2
        top = " ┌" + "─" * (inner + 2) + "┐"
        bot = " └" + "─" * (inner + 2) + "┘"
        safe_add(screen, line, 2, top, width - 3, THEME.attr(C_TITLE))
        line += 1

        def row(text: str = "", attr: int = 0) -> None:
            nonlocal line
            safe_add(
                screen,
                line,
                2,
                f" │ {text[:inner].ljust(inner)} │",
                width - 3,
                attr,
            )
            line += 1

        row(subtitle[:inner], THEME.attr(C_ACCENT, curses.A_BOLD))
        row()
        percent = float(state["percent"])
        bar_width = max(inner - 10, 10)
        row(
            f"{_progress_bar(percent, bar_width)}  {percent:5.1f}%",
            THEME.attr(C_OK, curses.A_BOLD),
        )
        row(
            f"{format_bytes(float(state['position']))} / {format_bytes(float(state['total']))}",
            THEME.attr(C_MUTED),
        )
        row(
            f"{format_bytes(float(state['rate']))}/s"
            f"   ·   {format_duration(float(state['elapsed']))}"
            f"   ·   ETA {format_duration(float(state['eta']))}",
            THEME.attr(C_MUTED),
        )
        detail = str(state.get("detail") or "")
        if detail:
            row()
            row(detail, THEME.attr(C_TITLE))
        if done and done_headline:
            row()
            row(
                done_headline,
                THEME.attr(C_OK if done_ok else C_WARN, curses.A_BOLD),
            )
        safe_add(screen, line, 2, bot, width - 3, THEME.attr(C_TITLE))
        foot = tr("progress_done_footer") if done else live_footer
        safe_add(screen, height - 1, 0, f" {foot}", width - 1, THEME.attr(C_FOOTER))
        screen.refresh()

    def on_update(info: dict[str, object]) -> None:
        state.update(info)
        draw()

    draw()
    try:
        work(on_update)
    except KeyboardInterrupt:
        done_ok = False

    if finish is not None:
        done_ok, done_headline, _detail = finish()
    elif not done_headline:
        done_headline = tr("index_created") if done_ok else tr("index_done_fail")

    done = True
    draw()

    while True:
        key = screen.getch()
        if key != -1:
            return done_ok


def run_export_progress(
    screen,
    title: str,
    node_count: int,
    work: Callable[[Callable[[dict[str, object]], None]], tuple[bool, str]],
    *,
    cancel: "threading.Event | None" = None,
) -> bool:
    """In-menu export progress: one stacked card per object.

    Export runs on a background thread so ↑↓ / mouse wheel can scroll the list
    while progress updates continue.
    """
    import threading

    THEME.init(screen)
    tr = i18n_mod.get_i18n().t
    slots: list[dict[str, object]] = [
        {
            "percent": 0.0,
            "step": "prepare",
            "node": "",
            "node_index": index + 1,
            "node_total": node_count,
            "detail": "",
            "finished": False,
        }
        for index in range(max(node_count, 1))
    ]
    done = False
    done_ok = True
    done_headline = ""
    scroll = 0
    lock = threading.Lock()
    result_holder: dict[str, object] = {}
    dirty = True

    step_labels = {
        "prepare": tr("export_step_prepare"),
        "closure": tr("export_step_closure"),
        "backward": tr("export_step_backward"),
        "write": tr("export_step_write"),
        "done": tr("export_step_done"),
    }

    def max_scroll(height: int) -> int:
        lines_per_slot = 4
        visible = max((height - 5) // lines_per_slot, 1)
        return max(0, len(slots) - visible)

    def draw() -> None:
        nonlocal scroll, dirty
        height, width = screen.getmaxyx()
        screen.erase()
        safe_add(screen, 0, 0, f" {title}", width - 1, THEME.attr(C_HEADER, curses.A_BOLD))

        inner = max(width - 8, 20)
        line = 2
        top = " ┌" + "─" * (inner + 2) + "┐"
        bot = " └" + "─" * (inner + 2) + "┘"
        safe_add(screen, line, 2, top, width - 3, THEME.attr(C_TITLE))
        line += 1

        def row(text: str = "", attr: int = 0) -> bool:
            nonlocal line
            if line >= height - 2:
                return False
            safe_add(
                screen,
                line,
                2,
                f" │ {text[:inner].ljust(inner)} │",
                width - 3,
                attr,
            )
            line += 1
            return True

        lines_per_slot = 4
        visible = max((height - 5) // lines_per_slot, 1)
        scroll = max(0, min(scroll, max_scroll(height)))
        visible_slots = slots[scroll : scroll + visible]

        for slot_offset, slot in enumerate(visible_slots):
            if slot_offset > 0 and not row("", THEME.attr(C_TITLE)):
                break
            node_name = str(slot.get("node") or "…")
            node_index = int(slot.get("node_index") or 0)
            node_total = int(slot.get("node_total") or node_count)
            if not row(
                tr("export_node_of", index=node_index, total=node_total, name=node_name),
                THEME.attr(C_ACCENT, curses.A_BOLD),
            ):
                break
            step = str(slot.get("step") or "prepare")
            detail = str(slot.get("detail") or "")
            step_text = step_labels.get(step, step)
            if detail:
                step_text = f"{step_text}  ·  {detail}"
            if not row(step_text, THEME.attr(C_TITLE)):
                break
            percent = float(slot.get("percent") or 0.0)
            bar_width = max(inner - 10, 10)
            finished = bool(slot.get("finished"))
            colour = C_OK if finished or percent >= 100.0 else C_OK
            if not row(
                f"{_progress_bar(percent, bar_width)}  {percent:5.1f}%",
                THEME.attr(colour, curses.A_BOLD),
            ):
                break

        if scroll > 0 or scroll + visible < len(slots):
            row(
                f"↑↓  {scroll + 1}-{scroll + len(visible_slots)} / {len(slots)}",
                THEME.attr(C_MUTED),
            )

        if done and done_headline:
            row()
            row(done_headline, THEME.attr(C_OK if done_ok else C_WARN, curses.A_BOLD))

        if line < height - 1:
            safe_add(screen, line, 2, bot, width - 3, THEME.attr(C_TITLE))
        foot = tr("progress_done_footer") if done else tr("progress_footer")
        safe_add(screen, height - 1, 0, f" {foot}", width - 1, THEME.attr(C_FOOTER))
        screen.refresh()
        dirty = False

    def on_update(info: dict[str, object]) -> None:
        nonlocal dirty
        with lock:
            slot_index = int(info.get("slot", int(info.get("node_index", 1)) - 1))
            if 0 <= slot_index < len(slots):
                slots[slot_index].update(info)
                if str(info.get("step")) == "done" or float(info.get("percent") or 0) >= 100.0:
                    slots[slot_index]["finished"] = True
            dirty = True

    def worker() -> None:
        try:
            ok, headline = work(on_update)
            result_holder["ok"] = ok
            result_holder["headline"] = headline
        except KeyboardInterrupt:
            result_holder["ok"] = False
            result_holder["headline"] = tr("export_done_cancel")
            result_holder["cancelled"] = True
        except Exception as error:  # noqa: BLE001 - keep the menu alive
            result_holder["ok"] = False
            result_holder["headline"] = str(error)
            result_holder["error"] = True

    def handle_scroll_key(key: int) -> bool:
        """Adjust scroll from a key/mouse event. Returns True if handled."""
        nonlocal scroll, dirty
        height, _width = screen.getmaxyx()
        limit = max_scroll(height)
        if key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
            dirty = True
            return True
        if key in (curses.KEY_DOWN, ord("j")):
            scroll = min(limit, scroll + 1)
            dirty = True
            return True
        if key == curses.KEY_NPAGE:
            scroll = min(limit, scroll + max((height - 5) // 4, 1))
            dirty = True
            return True
        if key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max((height - 5) // 4, 1))
            dirty = True
            return True
        if key == curses.KEY_MOUSE:
            try:
                _id, _x, _y, _z, button = curses.getmouse()
            except curses.error:
                return True
            if button & curses.BUTTON4_PRESSED:  # wheel up
                scroll = max(0, scroll - 1)
                dirty = True
            elif button & curses.BUTTON5_PRESSED:  # wheel down
                scroll = min(limit, scroll + 1)
                dirty = True
            return True
        return False

    old_mask = 0
    try:
        old_mask = curses.mousemask(
            curses.BUTTON4_PRESSED | curses.BUTTON5_PRESSED
        )[1]
    except curses.error:
        old_mask = 0

    screen.keypad(True)
    screen.nodelay(True)
    screen.timeout(100)

    thread = threading.Thread(target=worker, name="export-progress", daemon=True)
    thread.start()
    draw()

    try:
        while thread.is_alive():
            key = screen.getch()
            if key == -1:
                with lock:
                    if dirty:
                        draw()
                continue
            if key == 3:  # Ctrl+C delivered as character
                if cancel is not None:
                    cancel.set()
                continue
            with lock:
                handle_scroll_key(key)
                if dirty:
                    draw()
        thread.join(timeout=0.1)
    except KeyboardInterrupt:
        if cancel is not None:
            cancel.set()
        result_holder.setdefault("ok", False)
        result_holder.setdefault("headline", tr("export_done_cancel"))
        result_holder["cancelled"] = True
        thread.join(timeout=30.0)
    finally:
        screen.nodelay(False)
        screen.timeout(-1)
        try:
            curses.mousemask(old_mask)
        except curses.error:
            pass

    with lock:
        done = True
        done_ok = bool(result_holder.get("ok", False))
        done_headline = str(result_holder.get("headline") or "")
        if result_holder.get("cancelled") or (cancel is not None and cancel.is_set()):
            done_ok = False
            if not done_headline:
                done_headline = tr("export_done_cancel")
            for slot in slots:
                if not slot.get("finished"):
                    slot["detail"] = tr("export_done_cancel")
                    slot["step"] = "done"
        dirty = True
        draw()

    while True:
        key = screen.getch()
        with lock:
            if handle_scroll_key(key):
                draw()
                continue
        if key != -1:
            return done_ok


def run(app: Callable) -> int:
    """Run ``app(screen)`` inside curses and restore the terminal afterwards."""
    ensure_locale()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit(i18n_mod.get_i18n().t("tty_required"))
    try:
        return curses.wrapper(app)
    except KeyboardInterrupt:
        # Ctrl+C from any menu screen: exit quietly (curses already restored).
        return 130
