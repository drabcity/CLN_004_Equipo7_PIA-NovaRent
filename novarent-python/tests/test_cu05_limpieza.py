from novarent.aplicacion.comandos import MarcarVehiculoTerminado, RegistrarDevolucion
from novarent.aplicacion.consultas import ConsultarPanelDeVehiculos
from novarent.dominio import Dinero, EstatusDeVehiculo, TipoDeCargo, TransicionDeEstatusInvalida
from base import DIA, EscenarioBase, inspeccion


class TestCU05Limpieza(EscenarioBase):
    def setUp(self):
        super().setUp()
        self.agregar_reservacion(dias=1)
        self.agregar_vehiculo("v1")
        self.contrato_id = self.entregar()
        self.app.devolucion.registrar_devolucion(RegistrarDevolucion(self.contrato_id, inspeccion(km=1100), DIA))

    def estatus(self):
        return self.app.almacen.vehiculos["v1"].estatus

    def test_ciclo_completo_hasta_disponible(self):
        self.assertEqual(self.estatus(), EstatusDeVehiculo.EN_REVISION)
        self.app.limpieza.iniciar_limpieza("v1")
        self.assertEqual(self.estatus(), EstatusDeVehiculo.LIMPIEZA)
        self.assertEqual(self.app.limpieza.marcar_terminado(MarcarVehiculoTerminado("v1")), "v1")
        self.assertEqual(self.estatus(), EstatusDeVehiculo.DISPONIBLE)
        self.assertIn("VehiculoLiberado", self.app.publicador.nombres())

    def test_terminado_es_el_unico_camino_a_disponible(self):
        with self.assertRaises(TransicionDeEstatusInvalida):  # aun esta En revision
            self.app.limpieza.marcar_terminado(MarcarVehiculoTerminado("v1"))
        self.assertEqual(self.estatus(), EstatusDeVehiculo.EN_REVISION)

    def test_no_se_puede_iniciar_limpieza_de_un_vehiculo_rentado(self):
        self.app.almacen.vehiculos["v1"]._estatus = EstatusDeVehiculo.RENTADO
        with self.assertRaises(TransicionDeEstatusInvalida):
            self.app.limpieza.iniciar_limpieza("v1")

    def test_el_vehiculo_liberado_vuelve_a_poder_entregarse(self):
        self.app.limpieza.iniciar_limpieza("v1")
        self.app.limpieza.marcar_terminado(MarcarVehiculoTerminado("v1"))
        self.assertIsNotNone(self.app.entrega._disponibilidad.buscar_disponible_de_categoria(
            self.app.almacen.vehiculos["v1"].categoria))

    def test_mantenimiento_mayor_agrega_cargo_retroactivo_al_ultimo_contrato_por_evento(self):
        self.app.limpieza.iniciar_limpieza("v1")
        self.app.limpieza.reportar_mantenimiento_mayor("v1", "Vestiduras manchadas", Dinero.pesos(3000))
        self.assertEqual(self.estatus(), EstatusDeVehiculo.MANTENIMIENTO_MAYOR)
        contrato = self.app.almacen.contratos[self.contrato_id]
        retro = [c for c in contrato.cargos if c.tipo is TipoDeCargo.MANTENIMIENTO_MAYOR]
        self.assertEqual([c.monto for c in retro], [Dinero.pesos(3000)])
        self.assertEqual(retro[0].descripcion, "Vestiduras manchadas")

    def test_mantenimiento_mayor_solo_se_reporta_desde_limpieza(self):
        with self.assertRaises(TransicionDeEstatusInvalida):
            self.app.limpieza.reportar_mantenimiento_mayor("v1", "x", Dinero.pesos(1))

    def test_panel_de_vehiculos_es_una_query_de_solo_lectura(self):
        panel = self.app.panel(ConsultarPanelDeVehiculos())
        self.assertEqual([(p.vehiculo_id, p.estatus) for p in panel], [("v1", "En revision")])
        self.assertEqual(self.estatus(), EstatusDeVehiculo.EN_REVISION)
