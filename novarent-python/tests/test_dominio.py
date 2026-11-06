"""Pruebas del dominio solo, sin Service Layer ni infraestructura (se pueden correr aisladas)."""
import unittest

from novarent.dominio import (CalculadoraDeCargosExtra, Categoria, ContratoDeRenta, ContratoYaDevuelto, Dinero,
                              EsquemaDeDanosIncompleto, EstatusDeVehiculo, NivelDeCombustible, PeriodoDeRenta, Vehiculo,
                              VehiculoNoDisponible, VoucherAbierto, VoucherInvalido, TransicionDeEstatusInvalida)
from base import COMPACTA, DIA, inspeccion


class TestValoresYAggregates(unittest.TestCase):
    def test_dinero_en_centavos_sin_errores_de_punto_flotante(self):
        self.assertEqual(Dinero.pesos(10).porcentaje(20), Dinero.pesos(2))
        self.assertEqual(str(Dinero(12345)), "$123.45")

    def test_combustible_va_de_0_a_8_octavos(self):
        with self.assertRaises(ValueError):
            NivelDeCombustible(9)

    def test_voucher_exige_4_digitos_y_titular_igual_al_de_la_licencia(self):
        with self.assertRaises(VoucherInvalido):
            VoucherAbierto.crear("42", "AUT-1", "Ana", "Ana")
        with self.assertRaises(VoucherInvalido):
            VoucherAbierto.crear("4242", "AUT-1", "Beto", "Ana")
        self.assertEqual(VoucherAbierto.crear("4242", "AUT-1", "Ana", "Ana").titular, "Ana")

    def test_vehiculo_solo_se_entrega_si_esta_disponible(self):
        v = Vehiculo("v", "P", COMPACTA, 40, EstatusDeVehiculo.LIMPIEZA)
        with self.assertRaises(VehiculoNoDisponible):
            v.entregar(0)

    def test_vehiculo_no_salta_etapas(self):
        v = Vehiculo("v", "P", COMPACTA, 40)
        with self.assertRaises(TransicionDeEstatusInvalida):
            v.marcar_terminado(0)

    def test_contrato_no_se_crea_sin_esquema_completo(self):
        with self.assertRaises(EsquemaDeDanosIncompleto):
            ContratoDeRenta.crear("c", "r", "v", 40, Dinero.pesos(1000), VoucherAbierto("4242", "A", "Ana"),
                                  inspeccion(completo=False), PeriodoDeRenta(0, DIA))

    def test_el_contrato_no_cambia_el_estatus_del_vehiculo(self):
        """SOLID (S): cambiar al vehiculo lo coordina el servicio, no el contrato."""
        v = Vehiculo("v", "P", COMPACTA, 40)
        c = ContratoDeRenta.crear("c", "r", "v", 40, Dinero.pesos(1000), VoucherAbierto("4242", "A", "Ana"),
                                  inspeccion(), PeriodoDeRenta(0, DIA))
        c.registrar_devolucion(inspeccion(), DIA, Dinero.pesos(25), CalculadoraDeCargosExtra.estandar())
        self.assertIs(v.estatus, EstatusDeVehiculo.DISPONIBLE)
        with self.assertRaises(ContratoYaDevuelto):
            c.registrar_devolucion(inspeccion(), DIA, Dinero.pesos(25), CalculadoraDeCargosExtra.estandar())

    def test_agregar_una_politica_nueva_no_modifica_las_existentes(self):
        """SOLID (O): una politica nueva se agrega a la calculadora sin editar las otras."""
        from novarent.dominio import CargoExtra, PoliticaDeCargo, TipoDeCargo

        class CargoFijo(PoliticaDeCargo):
            def calcular(self, ctx):
                return CargoExtra(TipoDeCargo.DANOS, Dinero.pesos(1), "prueba")

        calc = CalculadoraDeCargosExtra.estandar()
        calc.agregar(CargoFijo())
        c = ContratoDeRenta.crear("c", "r", "v", 40, Dinero.pesos(1000), VoucherAbierto("4242", "A", "Ana"),
                                  inspeccion(), PeriodoDeRenta(0, DIA))
        c.registrar_devolucion(inspeccion(), DIA, Dinero.pesos(25), calc)
        self.assertEqual(c.total_cargos(), Dinero.pesos(1))


if __name__ == "__main__":
    unittest.main()
