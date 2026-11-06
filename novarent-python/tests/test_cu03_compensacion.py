from novarent.dominio import (CompensacionNoAplica, DecisionDelCliente, Dinero, EstatusDeReservacion, EstatusDeVehiculo,
                              TipoDeCompensacion)
from novarent.aplicacion.consultas import ConsultarOfertaDeCompensacion
from base import COMPACTA, ECONOMICA, SUV, EscenarioBase


class TestCU03Compensacion(EscenarioBase):
    """La categoria reservada (Compacta) no tiene unidades."""

    def setUp(self):
        super().setUp()
        self.agregar_reservacion(categoria=COMPACTA)
        self.agregar_vehiculo("c1", COMPACTA, EstatusDeVehiculo.RENTADO)

    def test_si_hay_upgrade_se_ofrece_primero_sin_costo(self):
        self.agregar_vehiculo("s1", SUV)
        dto = self.app.oferta(ConsultarOfertaDeCompensacion("res-1"))
        self.assertEqual((dto.tipo, dto.categoria_destino, dto.descuento_porcentaje), ("Upgrade", "SUV", 0))
        self.assertEqual(dto.tarifa_diaria, "$1000.00")  # paga la tarifa reservada

    def test_cliente_acepta_upgrade(self):
        self.agregar_vehiculo("s1", SUV)
        oferta = self.app.compensacion.resolver_categoria_no_disponible("res-1", DecisionDelCliente(acepta_upgrade=True))
        self.assertIs(oferta.tipo, TipoDeCompensacion.UPGRADE)
        r = self.app.almacen.reservaciones["res-1"]
        self.assertEqual((r.categoria, r.tarifa_diaria), (SUV, Dinero.pesos(1000)))
        self.assertIn("CategoriaCompensada", self.app.publicador.nombres())

    def test_sin_upgrade_se_ofrece_downgrade_con_20_por_ciento_de_descuento(self):
        self.agregar_vehiculo("e1", ECONOMICA)
        dto = self.app.oferta(ConsultarOfertaDeCompensacion("res-1"))
        self.assertEqual((dto.tipo, dto.categoria_destino, dto.descuento_porcentaje), ("Downgrade", "Economica", 20))
        self.assertEqual(dto.tarifa_diaria, "$400.00")  # 500 - 20%

    def test_cliente_rechaza_upgrade_y_acepta_downgrade(self):
        self.agregar_vehiculo("s1", SUV)
        self.agregar_vehiculo("e1", ECONOMICA)
        oferta = self.app.compensacion.resolver_categoria_no_disponible(
            "res-1", DecisionDelCliente(acepta_upgrade=False, acepta_downgrade=True))
        self.assertIs(oferta.tipo, TipoDeCompensacion.DOWNGRADE)
        self.assertEqual(self.app.almacen.reservaciones["res-1"].categoria, ECONOMICA)

    def test_cliente_rechaza_todo_se_cancela_la_reservacion(self):
        self.agregar_vehiculo("e1", ECONOMICA)
        self.app.compensacion.resolver_categoria_no_disponible("res-1", DecisionDelCliente())
        self.assertEqual(self.app.almacen.reservaciones["res-1"].estatus, EstatusDeReservacion.CANCELADA_POR_CATEGORIA_NO_DISPONIBLE)

    def test_sin_ninguna_alternativa_se_cancela(self):
        self.app.compensacion.resolver_categoria_no_disponible("res-1", DecisionDelCliente(True, True))
        self.assertEqual(self.app.almacen.reservaciones["res-1"].estatus, EstatusDeReservacion.CANCELADA_POR_CATEGORIA_NO_DISPONIBLE)

    def test_si_la_categoria_si_tiene_unidades_no_aplica(self):
        self.agregar_vehiculo("c2", COMPACTA)
        with self.assertRaises(CompensacionNoAplica):
            self.app.oferta(ConsultarOfertaDeCompensacion("res-1"))

    def test_la_query_no_cambia_el_estado(self):
        self.agregar_vehiculo("s1", SUV)
        self.app.oferta(ConsultarOfertaDeCompensacion("res-1"))
        self.assertEqual(self.app.almacen.reservaciones["res-1"].categoria, COMPACTA)
        self.assertEqual(self.app.publicador.publicados, [])
