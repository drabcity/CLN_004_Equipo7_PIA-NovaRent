"""Aggregate ContratoDeRenta. Raiz: ContratoDeRenta. Contiene voucher, periodo, inspecciones y cargos.

Invariantes: no se crea sin esquema de danos y al menos una foto (US05); el voucher esta a nombre
del titular de la licencia (US12); la devolucion se registra una sola vez.
El contrato NO cambia el estatus del vehiculo: eso lo coordina la Service Layer (SOLID: S).
"""
from __future__ import annotations

from .cargo_extra import CargoExtra, TipoDeCargo
from .comun import ContratoYaDevuelto, EsquemaDeDanosIncompleto, EventoDeDominio, Id, Minutos
from .politicas_de_cargo import CalculadoraDeCargosExtra, ContextoDeDevolucion
from .valores import Dinero, InspeccionDeVehiculo, PeriodoDeRenta, TarifaDiaria, VoucherAbierto


class ContratoDeRenta:
    def __init__(self, id: Id, reservacion_id: Id, vehiculo_id: Id, capacidad_tanque_litros: int, tarifa_diaria: TarifaDiaria,
                 voucher: VoucherAbierto, inspeccion_salida: InspeccionDeVehiculo, periodo: PeriodoDeRenta) -> None:
        # Se usa crear(): valida la invariante de salida y emite el evento.
        self._id = id
        self._reservacion_id = reservacion_id
        self._vehiculo_id = vehiculo_id
        self._capacidad_tanque_litros = capacidad_tanque_litros
        self._tarifa_diaria = tarifa_diaria
        self._voucher = voucher
        self._salida = inspeccion_salida
        self._periodo = periodo
        self._devolucion = InspeccionDeVehiculo()
        self._hora_devolucion: Minutos = 0
        self._devuelto = False
        self._cargos: list[CargoExtra] = []
        self._eventos: list[EventoDeDominio] = []

    @classmethod
    def crear(cls, id: Id, reservacion_id: Id, vehiculo_id: Id, capacidad_tanque_litros: int, tarifa_diaria: TarifaDiaria,
              voucher: VoucherAbierto, inspeccion_salida: InspeccionDeVehiculo, periodo: PeriodoDeRenta) -> "ContratoDeRenta":
        if not inspeccion_salida.esquema_valido():
            raise EsquemaDeDanosIncompleto()
        contrato = cls(id, reservacion_id, vehiculo_id, capacidad_tanque_litros, tarifa_diaria, voucher, inspeccion_salida, periodo)
        contrato._eventos.append(EventoDeDominio("VehiculoEntregado", id))
        return contrato

    def registrar_devolucion(self, inspeccion: InspeccionDeVehiculo, hora_devolucion: Minutos, precio_por_litro: Dinero,
                             calculadora: CalculadoraDeCargosExtra) -> None:
        """CU-04: registra la devolucion y calcula los cargos con las politicas (N3)."""
        if self._devuelto:
            raise ContratoYaDevuelto()
        ctx = ContextoDeDevolucion(self._tarifa_diaria, self._periodo, hora_devolucion, self._salida, inspeccion,
                                   self._capacidad_tanque_litros, precio_por_litro)
        self._cargos.extend(calculadora.calcular(ctx))
        self._devolucion = inspeccion
        self._hora_devolucion = hora_devolucion
        self._devuelto = True
        self._eventos.append(EventoDeDominio("VehiculoDevuelto", self._id))
        self._eventos.append(EventoDeDominio("CargosExtraCalculados", self._id))

    def registrar_cargo_manual(self, tipo: TipoDeCargo, monto: Dinero, descripcion: str) -> None:
        """Cargos sin regla de calculo automatica (danos: S-3)."""
        self._cargos.append(CargoExtra(tipo, monto, descripcion))

    def agregar_cargo_retroactivo(self, monto: Dinero, descripcion: str) -> None:
        """US13: cargo retroactivo por Mantenimiento Mayor (hasta cuando se permite: supuesto S-5)."""
        self._cargos.append(CargoExtra(TipoDeCargo.MANTENIMIENTO_MAYOR, monto, descripcion))

    def total_cargos(self) -> Dinero:
        total = Dinero()
        for c in self._cargos:
            if not c.cancelado:
                total = total + c.monto
        return total

    @property
    def id(self) -> Id:
        return self._id

    @property
    def reservacion_id(self) -> Id:
        return self._reservacion_id

    @property
    def vehiculo_id(self) -> Id:
        return self._vehiculo_id

    @property
    def periodo(self) -> PeriodoDeRenta:
        return self._periodo

    @property
    def voucher(self) -> VoucherAbierto:
        return self._voucher

    @property
    def cargos(self) -> tuple[CargoExtra, ...]:
        return tuple(self._cargos)

    @property
    def devuelto(self) -> bool:
        return self._devuelto

    def extraer_eventos(self) -> list[EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos
