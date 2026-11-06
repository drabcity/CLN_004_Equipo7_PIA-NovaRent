from novarent.aplicacion.comandos import RegistrarDevolucion
from novarent.aplicacion.consultas import ConsultarResumenDeCargos
from novarent.dominio import ContratoYaDevuelto, Dinero, EstatusDeVehiculo, TipoDeCargo
from base import DIA, EscenarioBase, inspeccion


class TestCU04Devolucion(EscenarioBase):
    """Renta de 2 dias, tarifa $1,000/dia (Compacta), tanque de 40 L, combustible a $25/L."""

    def setUp(self):
        super().setUp()
        self.agregar_reservacion(dias=2)
        self.agregar_vehiculo("v1")
        self.contrato_id = self.entregar()  # sale con 1000 km y tanque lleno

    def devolver(self, minutos_tarde=0, km=1400, octavos=8):
        cmd = RegistrarDevolucion(self.contrato_id, inspeccion(km=km, octavos=octavos), 2 * DIA + minutos_tarde)
        return self.app.devolucion.registrar_devolucion(cmd)

    def cargos(self):
        return {c.tipo: c for c in self.app.almacen.contratos[self.contrato_id].cargos}

    def test_devolucion_sin_cargos(self):
        self.devolver()
        self.assertEqual(self.cargos(), {})
        self.assertEqual(self.app.almacen.vehiculos["v1"].estatus, EstatusDeVehiculo.EN_REVISION)
        self.assertTrue({"VehiculoDevuelto", "CargosExtraCalculados"} <= set(self.app.publicador.nombres()))

    def test_retraso_dentro_de_la_tolerancia_de_120_minutos_no_cobra(self):
        self.devolver(minutos_tarde=120)
        self.assertNotIn(TipoDeCargo.RETRASO, self.cargos())

    def test_retraso_desde_el_minuto_121_cobra_20_por_ciento_por_hora(self):
        self.devolver(minutos_tarde=121)
        self.assertEqual(self.cargos()[TipoDeCargo.RETRASO].monto, Dinero.pesos(200))  # 1 h x 20% de $1,000

    def test_retraso_de_mas_de_4_horas_cobra_el_dia_completo(self):
        self.devolver(minutos_tarde=241)
        self.assertEqual(self.cargos()[TipoDeCargo.RETRASO].monto, Dinero.pesos(1000))

    def test_combustible_faltante_cobra_litros_por_precio_mas_100_pesos(self):
        self.devolver(octavos=4)  # faltan 4/8 de 40 L = 20 L x $25 = $500 + $100
        self.assertEqual(self.cargos()[TipoDeCargo.COMBUSTIBLE].monto, Dinero.pesos(600))

    def test_combustible_igual_o_mayor_al_entregado_no_cobra(self):
        self.devolver(octavos=8)
        self.assertNotIn(TipoDeCargo.COMBUSTIBLE, self.cargos())

    def test_kilometraje_250_por_dia_incluidos_y_5_pesos_por_km_extra(self):
        self.devolver(km=1000 + 600)  # 600 km - 500 incluidos (2 dias) = 100 km x $5
        self.assertEqual(self.cargos()[TipoDeCargo.KILOMETRAJE].monto, Dinero.pesos(500))

    def test_exactamente_250_km_por_dia_no_cobra(self):
        self.devolver(km=1000 + 500)
        self.assertNotIn(TipoDeCargo.KILOMETRAJE, self.cargos())

    def test_los_tres_cargos_juntos_y_el_resumen_de_la_query(self):
        self.devolver(minutos_tarde=180, km=1600, octavos=4)  # $200 + $600 + $500
        self.assertEqual(self.app.almacen.contratos[self.contrato_id].total_cargos(), Dinero.pesos(1300))
        resumen = self.app.resumen_cargos(ConsultarResumenDeCargos(self.contrato_id))
        self.assertEqual(resumen.total, "$1300.00")
        self.assertEqual([l.tipo for l in resumen.lineas], ["Retraso", "Combustible", "Kilometraje"])

    def test_un_contrato_ya_devuelto_no_se_devuelve_otra_vez_y_nada_cambia(self):
        self.devolver(minutos_tarde=180)
        antes = self.app.almacen.contratos[self.contrato_id].total_cargos()
        n_eventos = len(self.app.publicador.publicados)
        with self.assertRaises(ContratoYaDevuelto):
            self.devolver(minutos_tarde=600)
        self.assertEqual(self.app.almacen.contratos[self.contrato_id].total_cargos(), antes)
        self.assertEqual(len(self.app.publicador.publicados), n_eventos)

    def test_si_el_vehiculo_no_esta_rentado_se_revierte_la_devolucion(self):
        self.app.almacen.vehiculos["v1"]._estatus = EstatusDeVehiculo.LIMPIEZA
        with self.assertRaises(Exception):
            self.devolver(minutos_tarde=180)
        self.assertFalse(self.app.almacen.contratos[self.contrato_id].devuelto)  # rollback del contrato
