import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import reportes_db

ROOT = Path(__file__).resolve().parents[1]


def fila_exitosa(nombre, corte, llegada, ocurrencia=1):
    return {
        "grupo": nombre,
        "fecha_corte": corte,
        "fecha_llegada": llegada,
        "tipo_entidad": "TEST",
        "sigla": "TEST",
        "email": "",
        "resultado_raw": "",
        "validacion": "",
        "envio": f"Envío {ocurrencia}",
        "estado": "EXITOSO",
        "detalle": "",
        "timestamp_revision": llegada or "2026-09-23T13:00:00",
    }


class PrimeraInstalacionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test.db"
        reportes_db.initialize_database(self.db_path, ROOT / "reportes_seed.json")
        self.conn = reportes_db.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_cortes_desconocidos_primera_instalacion(self):
        # Instalación el miércoles 23/9 13:00: plazo mensual del 31/8 ya
        # vencido, semanal del domingo 20/9 vencido y diario del 22/9 vencido.
        current = datetime(2026, 9, 23, 13, 0)
        reportes_db.ensure_obligations(self.conn, current)

        desconocidos = reportes_db.list_unknown_period_cutoffs(self.conn, current)
        cortes = [item["fecha_corte"] for item in desconocidos]

        self.assertIn("2026-08-31", cortes)
        self.assertIn("2026-09-20", cortes)
        self.assertIn("2026-09-22", cortes)
        self.assertEqual(cortes, sorted(cortes))
        self.assertTrue(all(item["fecha_limite"] <= "2026-09-23" for item in desconocidos))

        rangos = reportes_db.get_query_date_ranges(
            self.conn,
            current,
            cortes_adicionales=[
                reportes_db.parse_date(item["fecha_corte"]) for item in desconocidos
            ],
        )
        self.assertIn((date(2026, 8, 31), date(2026, 8, 31)), rangos)
        self.assertIn((date(2026, 9, 20), date(2026, 9, 20)), rangos)

    def test_rango_manual_no_agrega_cortes_adicionales(self):
        current = datetime(2026, 9, 23, 13, 0)
        reportes_db.ensure_obligations(self.conn, current)
        rangos = reportes_db.get_query_date_ranges(
            self.conn,
            current,
            configured_start="2026-09-01",
            configured_end="2026-09-20",
            cortes_adicionales=[date(2026, 8, 31)],
        )
        self.assertEqual(rangos, [(date(2026, 9, 1), date(2026, 9, 20))])

    def test_primera_revision_resuelve_envios_previos(self):
        current = datetime(2026, 9, 23, 13, 0)
        obligaciones = reportes_db.ensure_obligations(self.conn, current)

        desconocidos = reportes_db.list_unknown_period_cutoffs(self.conn, current)
        self.assertTrue(desconocidos)

        # Como respondería ASFI: una fila exitosa por cada envío previamente
        # hecho, con llegada un poco antes del límite de cada obligación.
        grupos: dict[tuple[str, str], dict] = {}
        for obligacion in obligaciones:
            clave = (obligacion["codigo"], obligacion["fecha_corte"])
            entry = grupos.setdefault(
                clave,
                {
                    "nombre": obligacion["nombre"],
                    "limite": obligacion.get("fecha_hora_limite"),
                    "ocurrencias": 1,
                },
            )
            if obligacion.get("fecha_hora_limite"):
                entry["limite"] = obligacion.get("fecha_hora_limite")
            entry["ocurrencias"] = max(
                entry["ocurrencias"], obligacion["ocurrencia"] or 1
            )

        filas = []
        for (codigo, corte), entry in grupos.items():
            limite = reportes_db.parse_datetime(entry["limite"])
            if limite is None:
                continue
            llegada = limite.replace(
                hour=max(0, limite.hour - 1), minute=35, second=0
            )
            for ocurrencia in range(1, entry["ocurrencias"] + 1):
                filas.append(
                    fila_exitosa(
                        entry["nombre"],
                        corte,
                        llegada.strftime("%Y-%m-%d %H:%M:%S"),
                        ocurrencia,
                    )
                )
        self.assertTrue(filas)

        run_id = reportes_db.start_scrape_run(
            self.conn, date(2026, 8, 31), date(2026, 9, 22)
        )
        reportes_db.store_observations(self.conn, run_id, filas)
        evaluacion = reportes_db.evaluate_obligations(self.conn, filas, current)

        self.assertEqual(evaluacion["diario"], [])
        self.assertEqual(evaluacion["semanal"], [])
        self.assertEqual(evaluacion["mensual"], [])

        pendientes = self.conn.execute(
            "SELECT COUNT(*) FROM obligaciones WHERE estado NOT IN ('EXITOSO', 'DESCARTADO')"
        ).fetchone()[0]
        self.assertEqual(pendientes, 0)
        incumplimientos = self.conn.execute(
            "SELECT COUNT(*) FROM incumplimientos"
        ).fetchone()[0]
        self.assertEqual(incumplimientos, 0)

        # Tras la verificación ya no hay cortes pendientes de descubrir.
        self.assertEqual(
            reportes_db.list_unknown_period_cutoffs(self.conn, current),
            [],
        )

    def test_servicio_consulta_cortes_desconocidos(self):
        rangos_capturados = []
        # El reloj del servicio se fija a una instalación de mitad de mes,
        # conservando la zona horaria del local_now real.
        from asfi_monitor_app.storage.database import local_now as local_now_real

        def local_now_fijo():
            return local_now_real().replace(
                year=2026, month=9, day=23, hour=13, minute=0,
                second=0, microsecond=0,
            )

        def _obtener_reportes(rangos):
            rangos_capturados.extend(rangos)
            return []

        with (
            mock.patch(
                "asfi_monitor_app.storage.api.local_now",
                local_now_fijo,
            ),
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
                lambda: {"alertas_enviadas": {}},
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.guardar_estado",
                lambda *_: None,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.obtener_reportes_por_rangos",
                _obtener_reportes,
            ),
            mock.patch(
                "asfi_monitor_app.application.monitor_service.notificar",
                lambda titulo, mensaje, urgente=False: None,
            ),
        ):
            from asfi_monitor_app.application.monitor_service import ejecutar_revision

            ejecutar_revision()

        rangos_cubiertos = {corte for _inicio, corte in rangos_capturados}
        # Los cortes vencidos pendientes de la instalación deben ser consultados.
        self.assertIn(date(2026, 8, 31), rangos_cubiertos)
        self.assertIn(date(2026, 9, 22), rangos_cubiertos)


if __name__ == "__main__":
    unittest.main()
