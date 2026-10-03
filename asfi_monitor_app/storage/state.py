"""Persistencia del estado de alertas compatible con el JSON existente."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


def cargar_estado(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            pass
    return {"alertas_enviadas": {}, "ultima_revision": None}


def guardar_estado(path: Path, estado: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contenido = json.dumps(estado, ensure_ascii=False, indent=2, default=str)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(contenido)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def clave_reporte(reporte: dict) -> str:
    return f"{reporte['fecha_corte']}|{reporte['grupo']}|{reporte['envio']}"
