"""Bloqueos de archivo para evitar ejecuciones simultaneas del monitor."""

from __future__ import annotations

import os
from pathlib import Path


class InstanceLock:
    """Bloqueo portable que se libera automaticamente al cerrar el proceso."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._handle = None

    def acquire(self) -> bool:
        if self._handle is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:  # pragma: no cover - usado para pruebas fuera de Windows
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, IOError):
            handle.close()
            return False
        self._handle = handle
        return True

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:  # pragma: no cover - usado para pruebas fuera de Windows
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "InstanceLock":
        if not self.acquire():
            raise RuntimeError(f"El bloqueo ya está ocupado: {self.path}")
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.release()


class ReviewInProgress(RuntimeError):
    """Indica que otra instancia está ejecutando una revisión."""


def review_lock_path() -> Path:
    from asfi_monitor_app.storage import api as reportes_db

    return reportes_db.resolve_data_path("review.lock")


def monitor_lock_path() -> Path:
    from asfi_monitor_app.storage import api as reportes_db

    return reportes_db.resolve_data_path("monitor.lock")
