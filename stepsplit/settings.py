"""Persistent user settings and first-run defaults."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

SETTINGS_VERSION = 1
APP_DIR_NAME = "stepsplit"


@dataclass
class Settings:
    version: int = SETTINGS_VERSION
    setup_complete: bool = False
    language: str = "de"  # de | en
    color: bool = True

    # Export: beside_source | project_export | custom
    export_mode: str = "beside_source"
    export_dir: str = ""

    # Index work dir: cache | beside_source | custom
    work_mode: str = "cache"
    work_dir: str = ""

    last_source: str = ""
    overwrite_exports: bool = True
    # Prefix exported filenames with 1_, 2_, 3_, … in selection order.
    numbered_exports: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        known = {f.name for f in fields(cls)}
        cleaned = {key: value for key, value in data.items() if key in known}
        settings = cls(**cleaned)
        if settings.language not in {"de", "en"}:
            settings.language = "de"
        if settings.export_mode not in {"beside_source", "project_export", "custom"}:
            settings.export_mode = "beside_source"
        if settings.work_mode not in {"cache", "beside_source", "custom"}:
            settings.work_mode = "cache"
        return settings


def config_dir() -> Path:
    xdg = Path.home() / ".config" / APP_DIR_NAME
    try:
        xdg.mkdir(parents=True, exist_ok=True)
        return xdg
    except OSError:
        local = Path.cwd() / ".step-config"
        local.mkdir(parents=True, exist_ok=True)
        return local


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load_settings() -> Settings:
    path = settings_path()
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(data, dict):
        return Settings()
    return Settings.from_dict(data)


def save_settings(settings: Settings) -> Path:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def resolve_export_dir(settings: Settings, source: Path, fallback: Path | None = None) -> Path:
    if settings.export_mode == "custom" and settings.export_dir.strip():
        return Path(settings.export_dir).expanduser()
    if settings.export_mode == "project_export":
        return (fallback or Path("export")).expanduser()
    # beside_source
    if source.is_file():
        return source.resolve().parent / "export"
    return (fallback or Path("export")).expanduser()


def resolve_work_dir(settings: Settings, source: Path) -> Path:
    from .util import safe_filename

    name = f"{safe_filename(source.stem)}-{source.stat().st_size}" if source.is_file() else "unset"
    if settings.work_mode == "custom" and settings.work_dir.strip():
        base = Path(settings.work_dir).expanduser()
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        return path
    if settings.work_mode == "beside_source" and source.is_file():
        path = source.resolve().parent / ".step-work" / name
        path.mkdir(parents=True, exist_ok=True)
        return path
    preferred = Path.home() / ".cache" / APP_DIR_NAME / name
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        return preferred
    except OSError:
        local = (
            source.resolve().parent / ".step-work" / name
            if source.is_file()
            else Path.cwd() / ".step-work" / name
        )
        local.mkdir(parents=True, exist_ok=True)
        return local


def default_cache_root() -> Path:
    return Path.home() / ".cache" / APP_DIR_NAME


def resolve_cache_root(settings: Settings) -> Path:
    """Root folder that holds per-assembly index caches for the current mode."""
    if settings.work_mode == "custom" and settings.work_dir.strip():
        return Path(settings.work_dir).expanduser()
    if settings.work_mode == "beside_source":
        # Beside-source indexes live next to each STEP file; the central cache
        # under ~/.cache is still what this UI manages.
        return default_cache_root()
    return default_cache_root()


@dataclass
class CacheEntry:
    path: Path
    label: str
    source: str
    size_bytes: int
    created_label: str
    build_id: str


def _format_build_id(build_id: str) -> str:
    text = build_id.strip()
    if len(text) >= 15 and text[8] == "-":
        return (
            f"{text[0:4]}-{text[4:6]}-{text[6:8]} "
            f"{text[9:11]}:{text[11:13]}:{text[13:15]}"
        )
    return text


def list_cache_entries(root: Path | None = None) -> list[CacheEntry]:
    """List assembly index folders under the cache root."""
    from . import storage
    from .util import directory_size

    root = root or default_cache_root()
    if not root.is_dir():
        return []

    entries: list[CacheEntry] = []
    for child in sorted(root.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_dir() or child.name == "unset":
            continue
        db = storage.structure_db_path(child)
        try:
            has_content = db.exists() or any(child.iterdir())
        except OSError:
            continue
        if not has_content:
            continue
        source = ""
        build_id = ""
        if db.exists():
            try:
                connection = storage.connect_readonly(child)
                meta = storage.read_meta(connection)
                connection.close()
                source = str(meta.get("source", "") or "")
                build_id = str(meta.get("index_build_id", "") or "")
            except Exception:  # noqa: BLE001
                pass
        label = Path(source).name if source else child.name
        if build_id:
            created = _format_build_id(build_id)
        else:
            try:
                import time

                created = time.strftime(
                    "%Y-%m-%d %H:%M",
                    time.localtime(child.stat().st_mtime),
                )
            except OSError:
                created = "-"
        entries.append(
            CacheEntry(
                path=child,
                label=label,
                source=source,
                size_bytes=directory_size(child),
                created_label=created,
                build_id=build_id,
            )
        )
    return entries


def cache_total_size(root: Path | None = None) -> int:
    from .util import directory_size

    return directory_size(root or default_cache_root())
