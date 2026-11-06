from novarent.dominio import (DocumentacionInvalida, Dinero, EsquemaDeDanosIncompleto, EstatusDeReservacion,
                              EstatusDeVehiculo, VehiculoNoDisponible, VoucherInvalido)
from base import EscenarioBase, docs_validas, docs_vencidas, inspeccion


class TestCU02ValidarDocumentacion(EscenarioBase):
    def setUp(self):
        super().setUp()
        self.agregar_reservacion(pago=Dinero.pesos(1000))

    def test_documentacion_valida_permite_continuar(self):
        self.assertTrue(self.app.validacion.validar_documentacion_del_conductor("res-1", docs_validas()))
        r = self.app.almacen.reservaciones["res-1"]
        self.assertEqual(r.estatus, EstatusDeReservacion.CONFIRMADA)
        self.assertEqual(r.titular_licencia, "Ana Perez")  # la documentacion queda registrada

    def test_documentacion_invalida_cancela_y_retiene_10_por_ciento(self):
        self.assertFalse(self.app.validacion.validar_documentacion_del_conductor("res-1", docs_vencidas()))
        r = self.app.almacen.reservaciones["res-1"]
        self.assertEqual(r.estatus, EstatusDeReservacion.CANCELADA_POR_DOCUMENTACION_INVALIDA)
        self.assertEqual(r.retencion, Dinero.pesos(100))
        self.assertIn("DocumentacionInvalidaRegistrada", self.app.publicador.nombres())

    def test_menor_de_edad_es_documentacion_invalida(self):
        from dataclasses import replace
        menor = replace(docs_validas(), edad=17)
        self.assertFalse(self.app.validacion.validar_documentacion_del_conductor("res-1", menor))

    def test_identidad_no_verificada_es_invalida(self):
        from dataclasses import replace
        sin_verificar = replace(docs_validas(), identidad_verificada=False)
        self.assertFalse(self.app.validacion.validar_documentacion_del_conductor("res-1", sin_verificar))

    def test_una_reservacion_cancelada_ya_no_se_entrega(self):
        self.app.validacion.validar_documentacion_del_conductor("res-1", docs_vencidas())
        self.agregar_vehiculo("v1")
        with self.assertRaises(Exception):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega())


class TestCU01EntregarVehiculo(EscenarioBase):
    def setUp(self):
        super().setUp()
        self.agregar_reservacion()
        self.agregar_vehiculo("v1")
        self.app.validacion.validar_documentacion_del_conductor("res-1", docs_validas())

    def test_entrega_normal_cambia_los_tres_aggregates(self):
        contrato_id = self.app.entrega.entregar_vehiculo(self.cmd_entrega())
        a = self.app.almacen
        self.assertEqual(a.vehiculos["v1"].estatus, EstatusDeVehiculo.RENTADO)
        self.assertEqual(a.reservaciones["res-1"].estatus, EstatusDeReservacion.ENTREGADA)
        contrato = a.contratos[contrato_id]
        self.assertEqual(contrato.vehiculo_id, "v1")
        self.assertEqual(contrato.reservacion_id, "res-1")
        self.assertEqual(contrato.voucher.titular, "Ana Perez")
        self.assertEqual(contrato.voucher.codigo_autorizacion, self.app.banco.autorizaciones[0])
        self.assertIn("VehiculoEntregado", self.app.publicador.nombres())

    def test_esquema_incompleto_no_cambia_nada_y_libera_la_autorizacion(self):
        with self.assertRaises(EsquemaDeDanosIncompleto):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega(insp=inspeccion(completo=False)))
        self._nada_cambio()

    def test_sin_fotografia_no_se_firma_la_salida(self):
        with self.assertRaises(EsquemaDeDanosIncompleto):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega(insp=inspeccion(fotos=0)))
        self._nada_cambio()

    def test_tarjeta_a_nombre_de_otra_persona_se_rechaza(self):
        with self.assertRaises(VoucherInvalido):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega(titular_tarjeta="Otra Persona"))
        self._nada_cambio()

    def test_sin_vehiculo_disponible_en_la_categoria(self):
        self.app.almacen.vehiculos["v1"]._estatus = EstatusDeVehiculo.LIMPIEZA
        with self.assertRaises(VehiculoNoDisponible):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega())
        self.assertEqual(self.app.almacen.reservaciones["res-1"].estatus, EstatusDeReservacion.CONFIRMADA)

    def test_si_el_banco_rechaza_no_se_abre_ninguna_transaccion(self):
        self.app.banco.rechazar = True
        with self.assertRaises(RuntimeError):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega())
        self.assertEqual(self.app.almacen.vehiculos["v1"].estatus, EstatusDeVehiculo.DISPONIBLE)
        self.assertEqual(self.app.almacen.contratos, {})

    def test_no_se_entrega_con_documentacion_sin_registrar(self):
        self.agregar_reservacion("res-2")
        with self.assertRaises(DocumentacionInvalida):
            self.app.entrega.entregar_vehiculo(self.cmd_entrega("res-2"))
        self.assertEqual(self.app.banco.liberadas, self.app.banco.autorizaciones)

    def _nada_cambio(self):
        a = self.app.almacen
        self.assertEqual(a.vehiculos["v1"].estatus, EstatusDeVehiculo.DISPONIBLE)
        self.assertEqual(a.reservaciones["res-1"].estatus, EstatusDeReservacion.CONFIRMADA)
        self.assertEqual(a.contratos, {})
        self.assertNotIn("VehiculoEntregado", self.app.publicador.nombres())  # ningun evento sale sin commit
        self.assertEqual(self.app.banco.liberadas, self.app.banco.autorizaciones)  # compensacion


if __name__ == "__main__":
    import unittest
    unittest.main()
