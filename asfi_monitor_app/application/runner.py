"""Motor común para el agente de fondo, la GUI y la CLI."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import Event, Thread
from typing import Callable, Optional

from asfi_monitor_app.application import monitor_service as service

from .instance_lock import InstanceLock, ReviewInProgress, monitor_lock_path, review_lock_path


StatusCallback = Callable[[str], None]


@dataclass
class RunnerStatus:
    estado: str = "DETENIDO"
    ultima_revision: Optional[str] = None
    ultimo_error: Optional[str] = None


class MonitorRunner:
    """Ejecuta revisiones serializadas y permite detener el ciclo limpiamente."""

    def __init__(
        self,
        interval_provider: Optional[Callable[[], int]] = None,
        logger: Optional[logging.Logger] = None,
        on_status: Optional[StatusCallback] = None,
    ):
        self._interval_provider = interval_provider or self._configured_interval
        self._logger = logger or service.log
        self._on_status = on_status
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self.status = RunnerStatus()

    @staticmethod
    def _configured_interval() -> int:
        try:
            return max(1, int(service.CONFIG.get("intervalo_minutos", 15)))
        except (TypeError, ValueError):
            return 15

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _set_status(self, value: str, error: Optional[str] = None) -> None:
        self.status.estado = value
        if error is not None:
            self.status.ultimo_error = error
        if self._on_status is not None:
            try:
                self._on_status(value)
            except Exception:
                self._logger.debug("No se pudo actualizar el estado del runner", exc_info=True)

    def run_once(self) -> bool:
        """Ejecuta una revisión si no existe otra en curso."""
        lock = InstanceLock(review_lock_path())
        if not lock.acquire():
            raise ReviewInProgress("Ya existe una revisión en curso")
        self._set_status("REVISANDO")
        try:
            service.ejecutar_revision()
            self.status.ultima_revision = service.reportes_db.now_iso()
            self.status.ultimo_error = None
            self._set_status("LISTO")
            return True
        except Exception as exc:
            self.status.ultimo_error = str(exc)
            self._set_status("ERROR", str(exc))
            self._logger.error("Error en la revisión del monitor", exc_info=True)
            raise
        finally:
            lock.release()

    def run_forever(self, initial: bool = True) -> None:
        """Ejecuta el ciclo en el hilo actual hasta recibir una orden de parada."""
        self._stop_event.clear()
        self._set_status("ACTIVO")
        if initial:
            self._run_once_for_loop()
        while not self._stop_event.is_set():
            interval = self._interval_provider()
            self._logger.info("Próxima revisión en %s minuto(s)", interval)
            if self._stop_event.wait(interval * 60):
                break
            self._run_once_for_loop()
        self._set_status("DETENIDO")

    def _run_once_for_loop(self) -> None:
        try:
            self.run_once()
        except ReviewInProgress:
            self._logger.warning("Se omitió una revisión porque ya hay otra en curso")
        except Exception:
            # El agente debe seguir vivo aunque un ciclo falle.
            self._set_status("ERROR")

    def start(self, initial: bool = True) -> Thread:
        if self.running:
            return self._thread
        self._thread = Thread(
            target=self.run_forever,
            args=(initial,),
            name="asfi-monitor-runner",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        self._set_status("DETENIDO")


def run_continuous(
    interval_provider: Optional[Callable[[], int]] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Ejecuta el agente continuo con un único propietario del scheduler."""
    lock = InstanceLock(monitor_lock_path())
    if not lock.acquire():
        raise RuntimeError("ASFI Monitor ya está ejecutándose en este usuario")
    runner = MonitorRunner(interval_provider, logger)
    try:
        runner.run_forever()
    finally:
        runner.stop()
        lock.release()


def run_once_guarded() -> bool:
    """Ejecuta una revisión manual protegida contra concurrencia."""
    return MonitorRunner().run_once()
