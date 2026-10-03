import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from asfi_monitor_app.ui.pdf_export import export_analysis_pdf, prepare_analysis


class PdfExportTests(unittest.TestCase):
    def setUp(self):
        self.current = datetime(
            2026,
            9,
            16,
            15,
            30,
            tzinfo=timezone(timedelta(hours=-4)),
        )
        self.rows = [
            {
                "tipo_periodo": "diario",
                "nombre": "Reporte de prueba",
                "fecha_corte": "2026-09-15",
                "fecha_hora_limite": "2026-09-16T12:00:00-04:00",
                "fecha_envio": "2026-09-16T08:30:00-04:00",
                "estado": "EXITOSO",
            },
            {
                "tipo_periodo": "diario",
                "nombre": "Operaciones interbancarias",
                "fecha_corte": "2026-09-15",
                "fecha_hora_limite": "2026-09-16T12:00:00-04:00",
                "fecha_envio": None,
                "estado": "ABIERTO",
            },
        ]

    def test_prepare_analysis_uses_displayed_deadline_status(self):
        report = prepare_analysis(self.rows, self.current)

        self.assertEqual(report["total"], 2)
        self.assertEqual(report["counts"]["EXITOSO"], 1)
        self.assertEqual(report["counts"]["FALTANTE"], 1)
        self.assertEqual(report["rows"][1]["estado_mostrado"], "FALTANTE")

    def test_export_creates_readable_pdf_with_report_data(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "analisis.pdf"
            result = export_analysis_pdf(output, self.rows, self.current)
            content = result.read_bytes()

        self.assertEqual(result, output)
        self.assertTrue(content.startswith(b"%PDF-1.4"))
        self.assertIn(b"Reporte de prueba", content)
        self.assertIn("Operaciones interbancarias".encode("cp1252"), content)
        self.assertIn(b"%%EOF", content)


if __name__ == "__main__":
    unittest.main()
