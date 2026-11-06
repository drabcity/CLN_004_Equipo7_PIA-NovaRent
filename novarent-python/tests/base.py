"""Escenario comun de las pruebas: categorias, un vehiculo por categoria y una reservacion."""
import unittest

from novarent.aplicacion.comandos import EntregarVehiculo
from novarent.dominio import (Categoria, Dinero, DocumentacionConductor, InspeccionDeVehiculo, Kilometraje,
                              NivelDeCombustible, PeriodoDeRenta, Reservacion, Vehiculo)
from novarent.infraestructura.contenedor import construir_en_memoria

DIA = 1440
ECONOMICA = Categoria("Economica", 1, Dinero.pesos(500))
COMPACTA = Categoria("Compacta", 2, Dinero.pesos(1000))
SUV = Categoria("SUV", 3, Dinero.pesos(1500))


def docs_validas(ahora=0, titular="Ana Perez"):
    return DocumentacionConductor(titular, 30, ahora + 365 * DIA, ahora + 365 * DIA, identidad_verificada=True)


def docs_vencidas(titular="Ana Perez"):
    return DocumentacionConductor(titular, 30, -1, 365 * DIA, identidad_verificada=True)


def inspeccion(km=1000, octavos=8, fotos=2, completo=True):
    return InspeccionDeVehiculo(Kilometraje(km), NivelDeCombustible(octavos), 0, fotos, completo)


class EscenarioBase(unittest.TestCase):
    def setUp(self):
        self.app = construir_en_memoria(precio_por_litro=Dinero.pesos(25))
        self.app.almacen.categorias = [ECONOMICA, COMPACTA, SUV]

    def agregar_vehiculo(self, id, categoria=COMPACTA, estatus=None):
        v = Vehiculo(id, "PLACA-" + id, categoria, capacidad_tanque_litros=40) if estatus is None else \
            Vehiculo(id, "PLACA-" + id, categoria, 40, estatus)
        self.app.almacen.vehiculos[id] = v
        return v

    def agregar_reservacion(self, id="res-1", categoria=COMPACTA, dias=2, pago=Dinero.pesos(1000)):
        r = Reservacion(id, categoria, pago, PeriodoDeRenta(0, dias * DIA))
        self.app.almacen.reservaciones[id] = r
        return r

    def cmd_entrega(self, reservacion_id="res-1", titular_tarjeta="Ana Perez", insp=None):
        return EntregarVehiculo(reservacion_id, "4242", titular_tarjeta, insp or inspeccion())

    def entregar(self):
        """Deja una reservacion con documentacion valida y el vehiculo entregado. Devuelve el contrato_id."""
        self.app.validacion.validar_documentacion_del_conductor("res-1", docs_validas())
        return self.app.entrega.entregar_vehiculo(self.cmd_entrega())
