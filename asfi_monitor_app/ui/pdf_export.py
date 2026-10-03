"""Generación de informes PDF sin dependencias externas."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import textwrap
from typing import Iterable

from .formatters import _display_date, _display_datetime, _effective_status


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
LEFT_MARGIN = 40
RIGHT_MARGIN = 40
TOP_MARGIN = 40
BOTTOM_MARGIN = 42

STATUS_LABELS = {
    "EXITOSO": "OK",
    "ABIERTO": "ABIERTO",
    "PENDIENTE": "PENDIENTE",
    "EXITOSO_TARDIO": "EXITOSO TARDIO",
    "ERROR": "ERROR",
    "FALTANTE": "FALTANTE",
    "VENCIDO_SIN_ENVIAR": "VENCIDO",
    "CONFIGURAR": "CONFIGURAR",
}

PERIOD_LABELS = {
    "diario": "Diario",
    "semanal": "Semanal",
    "mensual": "Mensual",
    "trimestral": "Trimestral",
    "semestral": "Semestral",
    "anual": "Anual",
}


def prepare_analysis(rows: Iterable[dict], current: datetime) -> dict:
    """Prepara filas y totales para la vista previa y el PDF."""
    prepared = []
    for row in rows:
        item = dict(row)
        item["estado_mostrado"] = _effective_status(item, current)
        prepared.append(item)
    counts = Counter(item["estado_mostrado"] for item in prepared)
    return {"rows": prepared, "counts": dict(counts), "total": len(prepared)}


def export_analysis_pdf(
    path: str | Path, rows: Iterable[dict], current: datetime
) -> Path:
    """Escribe un PDF con el resultado de las obligaciones del análisis."""
    report = prepare_analysis(rows, current)
    pages = _build_pages(report, current)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(_encode_pdf(pages))
    return output


def _build_pages(report: dict, current: datetime) -> list[list[str]]:
    pages: list[list[str]] = []
    commands: list[str] = []
    page_number = 0
    y = PAGE_HEIGHT - TOP_MARGIN

    def start_page(continuation: bool = False) -> None:
        nonlocal commands, page_number, y
        if commands:
            _add_footer(commands, page_number)
            pages.append(commands)
        page_number += 1
        commands = []
        y = PAGE_HEIGHT - TOP_MARGIN
        _draw_text(
            commands,
            LEFT_MARGIN,
            y,
            "ASFI / SCIP Monitor",
            16,
            bold=True,
        )
        y -= 23
        _draw_text(
            commands,
            LEFT_MARGIN,
            y,
            "Informe de analisis de reportes" + (" (continuacion)" if continuation else ""),
            11,
        )
        y -= 18

    def add_line(text: str, size: int = 9, gap: int = 13) -> None:
        nonlocal y
        _draw_text(commands, LEFT_MARGIN, y, text, size)
        y -= gap

    start_page()
    add_line(f"Generado: {current.strftime('%d/%m/%Y %H:%M:%S')}", 9)
    add_line("Fuente: obligaciones y ultimo estado guardado en SQLite", 9)
    y -= 8
    _draw_text(commands, LEFT_MARGIN, y, "Resumen", 11, bold=True)
    y -= 17
    counts = report["counts"]
    add_line(
        f"Total: {report['total']}   |   OK: {counts.get('EXITOSO', 0)}   |   "
        f"Errores: {counts.get('ERROR', 0)}",
        9,
    )
    add_line(
        f"Faltantes: {counts.get('FALTANTE', 0)}   |   "
        f"Pendientes: {counts.get('PENDIENTE', 0)}",
        9,
    )
    add_line(
        f"Vencidos: {counts.get('VENCIDO_SIN_ENVIAR', 0)}   |   "
        f"Tardios: {counts.get('EXITOSO_TARDIO', 0)}",
        9,
    )
    y -= 9
    y = _draw_table_header(commands, y)

    for row in report["rows"]:
        name = str(row.get("nombre") or row.get("codigo") or "Reporte sin nombre")
        name_lines = textwrap.wrap(
            name,
            width=43,
            break_long_words=False,
            break_on_hyphens=False,
        ) or ["-"]
        row_height = max(1, len(name_lines)) * 12 + 5
        if y - row_height < BOTTOM_MARGIN + 18:
            start_page(continuation=True)
            y = _draw_table_header(commands, y)

        tipo = PERIOD_LABELS.get(str(row.get("tipo_periodo") or "").lower(), "Otro")
        corte = _display_date(row.get("fecha_corte"))
        limite = _display_datetime(row.get("fecha_hora_limite"))
        envio = _display_datetime(row.get("fecha_envio"))[:10]
        estado = STATUS_LABELS.get(row["estado_mostrado"], row["estado_mostrado"])
        for index, line in enumerate(name_lines):
            line_y = y - index * 12
            _draw_text(commands, 40, line_y, tipo if index == 0 else "", 8)
            _draw_text(commands, 90, line_y, line, 8)
            _draw_text(commands, 340, line_y, corte if index == 0 else "", 8)
            _draw_text(commands, 410, line_y, limite if index == 0 else "", 8)
            _draw_text(commands, 490, line_y, estado if index == 0 else "", 8)
            _draw_text(commands, 548, line_y, envio if index == 0 else "", 7)
        y -= row_height

    if not report["rows"]:
        _draw_text(commands, LEFT_MARGIN, y, "No hay obligaciones para mostrar.", 9)
    _add_footer(commands, page_number)
    pages.append(commands)
    return pages


def _draw_table_header(commands: list[str], y: int) -> int:
    _draw_text(commands, 40, y, "Tipo", 8, bold=True)
    _draw_text(commands, 90, y, "Reporte", 8, bold=True)
    _draw_text(commands, 340, y, "Corte", 8, bold=True)
    _draw_text(commands, 410, y, "Limite", 8, bold=True)
    _draw_text(commands, 490, y, "Estado", 8, bold=True)
    _draw_text(commands, 548, y, "Envio", 7, bold=True)
    return y - 15


def _add_footer(commands: list[str], page_number: int) -> None:
    _draw_text(commands, LEFT_MARGIN, 25, "ASFI / SCIP Monitor - Informe generado localmente", 7)
    _draw_text(commands, PAGE_WIDTH - 82, 25, f"Pagina {page_number}", 7)


def _draw_text(
    commands: list[str], x: int, y: int, text: str, size: int, bold: bool = False
) -> None:
    font = "/F2" if bold else "/F1"
    commands.append(f"BT {font} {size} Tf {x} {y} Td {_pdf_literal(text)} Tj ET")


def _pdf_literal(value: str) -> str:
    # Helvetica usa WinAnsi; se reemplazan caracteres fuera de esa codificación
    # para mantener el PDF legible sin instalar fuentes adicionales.
    encoded = str(value).encode("cp1252", errors="replace").decode("latin-1")
    return "(" + encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def _encode_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    page_ids = []
    for commands in pages:
        page_id = len(objects) + 1
        content_id = page_id + 1
        content = "\n".join(commands).encode("latin-1")
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content
            + b"\nendstream"
        )
        page_ids.append(page_id)

    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_ids)} >>"
    ).encode("ascii")

    output = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_offset = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    output += b"0000000000 65535 f \n"
    output += b"".join(f"{offset:010d} 00000 n \n".encode("ascii") for offset in offsets[1:])
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return output
