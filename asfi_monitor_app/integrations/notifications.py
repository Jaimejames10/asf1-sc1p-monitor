"""Adaptadores de notificacion para Windows y Plyer."""

from __future__ import annotations

import logging
import html
import os
from pathlib import Path
import subprocess
from typing import Optional


APP_USER_MODEL_ID = "ASFI.Monitor"


def notificar(
    titulo: str,
    mensaje: str,
    urgente: bool = False,
    *,
    logger: Optional[logging.Logger] = None,
    icon_path: Optional[Path] = None,
) -> None:
    """Envía una alerta usando el primer proveedor disponible."""
    log = logger or logging.getLogger("asfi_monitor")

    titulo_log = titulo.encode("ascii", "replace").decode("ascii")
    mensaje_log = mensaje[:100].encode("ascii", "replace").decode("ascii")
    log.info(f"[NOTIFICACION] {titulo_log}: {mensaje_log}")

    titulo_limpio = titulo[:128]
    mensaje_limpio = mensaje[:512]
    titulo_ps = titulo_limpio.replace("'", "''")
    mensaje_ps = mensaje_limpio.replace("'", "''")

    def metodo_toast_nativo():
        try:
            if os.name != "nt":
                return False
            toast_title = html.escape(titulo_limpio, quote=True)
            toast_message = html.escape(mensaje_limpio, quote=True).replace("\n", "&#10;")
            ps_script = f"""
            [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
            [void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml('<toast><visual><binding template="ToastGeneric"><text>{toast_title}</text><text>{toast_message}</text></binding></visual></toast>')
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_USER_MODEL_ID}')
            $notifier.Show($toast)
            """
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", ps_script],
                timeout=15,
                capture_output=True,
                text=True,
                creationflags=flags,
            )
            if result.returncode == 0:
                log.debug("Notificacion enviada via Windows Toast nativo")
                return True
            log.debug("Windows Toast nativo devolvio codigo %s", result.returncode)
            return False
        except Exception as exc:
            log.debug(f"Windows Toast nativo: {type(exc).__name__}")
            return False

    def metodo_plyer():
        try:
            from plyer import notification

            duracion = 30 if urgente else 15
            notification.notify(
                title=titulo_limpio,
                message=mensaje_limpio[:256],
                app_name="ASFI/SCIP Monitor",
                app_icon=str(icon_path) if icon_path else None,
                timeout=duracion,
            )
            log.debug(f"Notificacion enviada via plyer ({duracion}s)")
            return True
        except Exception as exc:
            log.debug(f"plyer: {type(exc).__name__}")
            return False

    def metodo_ballontip():
        try:
            duracion_ms = 15000 if urgente else 10000
            espera_s = 16 if urgente else 11
            if icon_path:
                icono_ps = str(icon_path).replace("'", "''")
                linea_icono = f"$n.Icon = New-Object System.Drawing.Icon('{icono_ps}')"
            else:
                linea_icono = "$n.Icon = [System.Drawing.SystemIcons]::Warning"
            ps_script = f"""
            Add-Type -AssemblyName System.Windows.Forms
            Add-Type -AssemblyName System.Drawing
            $n = New-Object System.Windows.Forms.NotifyIcon
            {linea_icono}
            $n.BalloonTipTitle = '{titulo_ps}'
            $n.BalloonTipText = '{mensaje_ps}'
            $n.Visible = $True
            $n.ShowBalloonTip({duracion_ms})
            Start-Sleep -Seconds {espera_s}
            $n.Visible = $False
            """
            subprocess.Popen(
                ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            log.debug(f"Notificacion enviada via fallback BalloonTip ({duracion_ms}ms)")
            return True
        except Exception as exc:
            log.debug(f"PowerShell BalloonTip: {type(exc).__name__}")
            return False

    if urgente:
        log.info("[URGENTE] Enviando notificacion por un metodo disponible...")
        if metodo_toast_nativo() or metodo_plyer() or metodo_ballontip():
            return
    elif metodo_toast_nativo() or metodo_plyer() or metodo_ballontip():
        return
    log.warning(f"No se pudo mostrar notificacion: {titulo}")
