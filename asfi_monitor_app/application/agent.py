"""Punto de entrada del agente de fondo iniciado al iniciar sesión."""

from __future__ import annotations

import logging
import time

from . import bootstrap
from . import monitor_service as service
from .runner import run_continuous


def main() -> int:
    while True:
        try:
            bootstrap.prepare_monitor()
            bootstrap.verify_playwright()
            break
        except bootstrap.MissingCredentials as exc:
            service.log.warning(
                "El agente espera credenciales configuradas desde la GUI: %s", exc
            )
            time.sleep(30)
        except Exception as exc:
            service.log.error("No se pudo iniciar el agente de fondo: %s", exc)
            return 1

    service.log.info("Agente de fondo ASFI Monitor iniciado al iniciar sesión")
    service.notificar(
        "ASFI/SCIP Monitor iniciado",
        f"Monitoreando reportes cada {service.CONFIG['intervalo_minutos']} min.",
    )
    try:
        run_continuous(logger=logging.getLogger("asfi_monitor"))
    except KeyboardInterrupt:
        service.log.info("Agente de fondo detenido")
    except RuntimeError as exc:
        service.log.error("No se pudo ejecutar el agente de fondo: %s", exc)
        return 1
    return 0
