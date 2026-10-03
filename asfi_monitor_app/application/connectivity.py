"""Detección de conexión a internet para el monitor ASFI/SCIP.

Una revisión sin conexión produce falsos faltantes: la consulta a SCIP no
devuelve filas y las obligaciones abiertas se califican como no enviadas.
Con esta sonda el monitor salta los ciclos sin internet, avisa al usuario y
conserva la base de datos intacta hasta que la conexión vuelva.
"""

from __future__ import annotations

import logging
import socket
from urllib.parse import urlparse

log = logging.getLogger(__name__)

# Segundos máximos de espera por servidor de sonda.
PROBE_TIMEOUT = 5.0

# Sondas públicas para confirmar la conexión cuando el sitio de ASFI
# mismo no responde (p. ej. por una caída propia del servidor).
SERVIDORES_FALLBACK: tuple[tuple[str, int], ...] = (
    ("8.8.8.8", 53),
    ("1.1.1.1", 53),
)

# Indicios en mensajes de excepción de que el problema fue de red.
PATRONES_CONEXION: tuple[str, ...] = (
    "internet disconnected",
    "internet_disconnected",
    "name not resolved",
    "err_name_not_resolved",
    "getaddrinfo failed",
    "connection refused",
    "connection reset",
    "no route to host",
    "host unreachable",
    "network unreachable",
    "timed out",
    "timeout",
    "ssl",
)


def _objetivos(url_base: str = "") -> list[tuple[str, int]]:
    """Servidores a intentar: primero ASFI, después sondas públicas."""
    objetivos: list[tuple[str, int]] = []
    try:
        parsed = urlparse(url_base or "")
    except ValueError:
        parsed = None
    if parsed is not None and parsed.hostname:
        port = parsed.port
        if port is None:
            port = 80 if parsed.scheme in ("http", "") else 443
        objetivos.append((parsed.hostname, port))
    objetivos.extend(SERVIDORES_FALLBACK)
    return objetivos


def hay_conexion(url_base: str = "") -> bool:
    """True si algún servidor de Internet está conectado."""
    for host, port in _objetivos(url_base):
        try:
            with socket.create_connection((host, port), timeout=PROBE_TIMEOUT):
                return True
        except OSError as exc:
            log.debug("Sonda %s:%s falló: %s", host, port, exc)
    return False


def parece_problema_de_conexion(exc: BaseException) -> bool:
    """Indica si la excepción parece provenir de un corte de red."""
    texto = f"{type(exc).__name__}: {exc}".lower()
    return any(patron in texto for patron in PATRONES_CONEXION)
