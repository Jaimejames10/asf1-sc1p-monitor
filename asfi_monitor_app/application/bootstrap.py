"""Inicialización compartida por la CLI y el agente de Windows."""

from __future__ import annotations

import os
from pathlib import Path

from asfi_monitor_app.application import monitor_service as service


class MissingCredentials(RuntimeError):
    """Indica que el usuario todavía no configuró sus credenciales."""


def prepare_monitor(
    *,
    interval: int | None = None,
    visible: bool = False,
    verbose: bool = False,
    days: int | None = None,
    username: str | None = None,
    password: str | None = None,
) -> Path:
    """Carga configuración, credenciales y opciones antes de revisar."""
    config = service.CONFIG
    service.configurar_salida_consola(verbose)
    config["_verbose"] = verbose
    db_path = service.inicializar_base_datos()
    service.cargar_configuracion_desde_db(db_path)

    try:
        usuario_db, password_db = service.cargar_credenciales_desde_db(db_path)
    except Exception as exc:
        raise RuntimeError(f"No se pudieron leer las credenciales de SQLite: {exc}") from exc

    if not config["usuario"]:
        config["usuario"] = usuario_db
    if not config["password"]:
        config["password"] = password_db
    if interval is not None:
        if interval <= 0:
            raise ValueError("El intervalo debe ser mayor que cero")
        config["intervalo_minutos"] = interval
    config["_intervalo_fijado_cli"] = interval is not None
    config["headless"] = not visible
    if days is not None:
        if days < 0:
            raise ValueError("Los días hacia atrás no pueden ser negativos")
        config["dias_atras"] = days
    if username:
        config["usuario"] = username
    if password:
        config["password"] = password
    config["_usar_credenciales_db"] = not (
        bool(username)
        or bool(password)
        or bool(os.environ.get("ASFI_USUARIO"))
        or bool(os.environ.get("ASFI_PASSWORD"))
    )

    if not config["usuario"] or not config["password"]:
        raise MissingCredentials(
            "No se configuraron las credenciales. Use la GUI, ASFI_USUARIO/ASFI_PASSWORD "
            "o los argumentos --usuario y --password."
        )
    return db_path


def verify_playwright() -> None:
    """Comprueba que el cliente Playwright esté disponible."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Playwright no está instalado o no fue incluido en la instalación."
        ) from exc
