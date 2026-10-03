"""Conexion SQLite, rutas de datos y reloj local del monitor."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import shutil
import sys

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_NAME = "ASFI Monitor"
DEFAULT_TIMEZONE = "America/La_Paz"
try:
    LOCAL_TIMEZONE = ZoneInfo(DEFAULT_TIMEZONE) if ZoneInfo else timezone(
        timedelta(hours=-4), DEFAULT_TIMEZONE
    )
except Exception:  # Windows puede no tener tzdata instalado
    LOCAL_TIMEZONE = timezone(timedelta(hours=-4), DEFAULT_TIMEZONE)


def is_frozen() -> bool:
    """Indica si la aplicación está ejecutándose desde un empaquetado."""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """Devuelve la carpeta de recursos de solo lectura."""
    bundled_root = getattr(sys, "_MEIPASS", None)
    return Path(bundled_root) if bundled_root else PROJECT_ROOT


def user_data_root() -> Path:
    """Devuelve la carpeta escribible del perfil del usuario."""
    configured = os.environ.get("ASFI_MONITOR_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    if not is_frozen():
        return PROJECT_ROOT
    local_app_data = os.environ.get("LOCALAPPDATA")
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / APP_NAME


def resolve_resource_path(path: str | Path) -> Path:
    """Resuelve un recurso incluido con la aplicación."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else resource_root() / candidate


def resolve_data_path(path: str | Path) -> Path:
    """Resuelve un archivo modificable en el perfil del usuario."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else user_data_root() / candidate


def resolve_path(path: str | Path) -> Path:
    """Compatibilidad: resuelve rutas relativas como archivos de datos."""
    return resolve_data_path(path)


def ensure_user_data_dirs() -> Path:
    """Crea las carpetas de datos necesarias y devuelve la raíz de usuario."""
    root = user_data_root()
    for directory in (root, root / "logs", root / "exports", root / "backups"):
        directory.mkdir(parents=True, exist_ok=True)
    return root


def configure_playwright_browser_path() -> Path | None:
    """Configura Chromium incluido junto al ejecutable empaquetado."""
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or not is_frozen():
        return None
    candidates = [
        resource_root() / "ms-playwright",
        Path(sys.executable).resolve().parent / "ms-playwright",
        Path(sys.executable).resolve().parents[1] / "ms-playwright",
    ]
    for candidate in candidates:
        if _contains_playwright_browser(candidate):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(candidate)
            return candidate
    return None


def _contains_playwright_browser(path: Path) -> bool:
    """Evita seleccionar carpetas vacías creadas por el instalador."""
    if not path.is_dir():
        return False
    return any(path.glob("chromium_headless_shell-*/*/chrome-headless-shell.exe")) or any(
        path.glob("chromium-*/*/chrome.exe")
    )


def migrate_legacy_data(legacy_roots: list[Path] | None = None) -> list[Path]:
    """Copia datos legacy al perfil instalado cuando es seguro hacerlo."""
    if not is_frozen():
        return []
    target_root = ensure_user_data_dirs()
    copied: list[Path] = []
    roots = legacy_roots or [
        PROJECT_ROOT,
        Path.home() / "Downloads" / "Reports_ASFI_monitor",
        Path.home() / "Documents" / "Reports_ASFI_monitor",
    ]
    for legacy_root in roots:
        legacy_root = Path(legacy_root)
        if legacy_root.resolve() == target_root.resolve():
            continue
        source_db = legacy_root / "asfi_monitor.db"
        target_db = target_root / "asfi_monitor.db"
        if source_db.exists() and not target_db.exists():
            import sqlite3

            source_conn = sqlite3.connect(str(source_db))
            target_conn = sqlite3.connect(str(target_db))
            try:
                try:
                    source_conn.backup(target_conn)
                    target_conn.commit()
                    copied.append(target_db)
                except sqlite3.Error:
                    target_conn.close()
                    target_conn = None
                    target_db.unlink(missing_ok=True)
            finally:
                source_conn.close()
                if target_conn is not None:
                    target_conn.close()
        for filename in ("asfi_estado.json", "reportes_no_enviados.json"):
            source = legacy_root / filename
            target = target_root / filename
            if source.exists() and not target.exists():
                shutil.copy2(source, target)
                copied.append(target)
        if target_db.exists():
            break
    return copied


def local_now() -> datetime:
    """Obtiene la hora local de Bolivia."""
    return datetime.now(LOCAL_TIMEZONE) if LOCAL_TIMEZONE else datetime.now()


def now_iso(value: datetime | None = None) -> str:
    value = value or local_now()
    return value.isoformat(timespec="seconds")


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Abre SQLite con las mismas politicas WAL usadas por el monitor."""
    path = resolve_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
