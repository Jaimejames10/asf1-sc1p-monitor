import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import reportes_db
from asfi_monitor_app.application import connectivity
from asfi_monitor_app.application.monitor_service import ejecutar_revision

ROOT = Path(__file__).resolve().parents[1]


class ConnectivityTests(unittest.TestCase):
    def test_hay_conexion_true_when_any_probe_opens(self):
        def fake_create_connection(direccion, timeout=None):
            if direccion[0] == "appweb.asfi.gob.bo":
                raise OSError("sin ruta")
            return mock.MagicMock()

        with mock.patch.object(
            connectivity.socket, "create_connection", side_effect=fake_create_connection
        ):
            self.assertTrue(connectivity.hay_conexion("https://appweb.asfi.gob.bo/SCIP"))

    def test_hay_conexion_false_when_all_probes_fail(self):
        with mock.patch.object(
            connectivity.socket,
            "create_connection",
            side_effect=OSError("red caída"),
        ):
            self.assertFalse(connectivity.hay_conexion("https://appweb.asfi.gob.bo/SCIP"))

    def test_parece_problema_de_conexion(self):
        self.assertTrue(connectivity.parece_problema_de_conexion(TimeoutError("timed out")))
        self.assertTrue(
            connectivity.parece_problema_de_conexion(
                Exception("net::ERR_INTERNET_DISCONNECTED en login")
            )
        )
        self.assertFalse(connectivity.parece_problema_de_conexion(ValueError("boom")))


class RevisionSinInternetTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test.db"
        reportes_db.initialize_database(self.db_path, ROOT / "reportes_seed.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_revision_omitida_cuando_no_hay_conexion(self):
        avisos = []
        reportes = mock.Mock(side_effect=AssertionError("No debe consultarse ASFI sin conexión"))

        with (
            mock.patch(
                "asfi_monitor_app.application.monitor_service.inicializar_base_datos",
                lambda *_: self.db_path,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.cargar_configuracion_desde_db",
                lambda *_: None,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.cargar_credenciales_desde_db",
                lambda *_: ("u", "p"),
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.hay_conexion",
                lambda *_: False,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.cargar_estado",
                lambda: {},
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.guardar_estado",
                mock.Mock(side_effect=AssertionError("Sin conexión el estado no cambia")),
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.obtener_reportes_por_rangos",
                reportes,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.notificar",
                lambda titulo, mensaje, urgente=False: avisos.append((titulo, mensaje, urgente)),
            ),
        ):
            ejecutar_revision()

        reportes.assert_not_called()
        titulos = [item[0] for item in avisos]
        self.assertIn("🟠 ASFI/SCIP Monitor - Sin internet", titulos)

        # La base debe quedar sin marcas de FALTANTE por este ciclo.
        conn = reportes_db.connect(self.db_path)
        try:
            faltantes = conn.execute(
                "SELECT COUNT(*) FROM obligaciones WHERE estado = 'FALTANTE'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(faltantes, 0)

    def test_corte_de_conexion_al_consultar_avis_sin_marcar_faltantes(self):
        avisos = []

        with TemporaryDirectory() as area:
            archivo_estado = Path(area) / "estado.json"

            def _guardar_estado(estado):
                archivo_estado.write_text("{}", encoding="utf-8")

            with (
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.inicializar_base_datos",
                    lambda *_: self.db_path,
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.cargar_configuracion_desde_db",
                    lambda *_: None,
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.cargar_credenciales_desde_db",
                    lambda *_: ("u", "p"),
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.hay_conexion",
                    lambda *_: True,
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.cargar_estado",
                    lambda: {},
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.guardar_estado",
                    _guardar_estado,
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.obtener_reportes_por_rangos",
                    mock.Mock(side_effect=Exception("net::ERR_INTERNET_DISCONNECTED")),
                ),
                mock.patch(
                    "asfi_monitor_app.application.monitor_service.notificar",
                    lambda titulo, mensaje, urgente=False: avisos.append(
                        (titulo, mensaje, urgente)
                    ),
                ),
            ):
                ejecutar_revision()

        titulos = [item[0] for item in avisos]
        self.assertIn("🟠 ASFI/SCIP Monitor - Sin internet", titulos)
        self.assertNotIn("🔴 ASFI/SCIP Monitor - Fallo crítico", titulos)

        conn = reportes_db.connect(self.db_path)
        try:
            faltantes = conn.execute(
                "SELECT COUNT(*) FROM obligaciones WHERE estado = 'FALTANTE'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(faltantes, 0)


if __name__ == "__main__":
    unittest.main()
