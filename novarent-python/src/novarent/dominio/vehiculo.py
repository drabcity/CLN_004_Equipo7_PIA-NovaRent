"""Aggregate Vehiculo (glosario #17). Raiz: Vehiculo.

Invariantes: solo un vehiculo 'Disponible' se entrega (N2); solo se llega a 'Disponible' desde
'Limpieza' cuando se marca 'Terminado' (US11).
Transiciones: Disponible -> Rentado -> En revision -> Limpieza -> Disponible | Mantenimiento Mayor.
(La salida de Mantenimiento Mayor no esta definida en la Unidad 2: supuesto S-4.)
"""
from __future__ import annotations

from .comun import EventoDeDominio, Id, Minutos, TransicionDeEstatusInvalida, VehiculoNoDisponible
from .valores import Categoria, Dinero, EstatusDeVehiculo


class Vehiculo:
    def __init__(self, id: Id, placa: str, categoria: Categoria, capacidad_tanque_litros: int,
                 estatus: EstatusDeVehiculo = EstatusDeVehiculo.DISPONIBLE, desde: Minutos = 0) -> None:
        self._id = id
        self._placa = placa
        self._categoria = categoria
        self._capacidad_tanque_litros = capacidad_tanque_litros  # supuesto S-2
        self._estatus = estatus
        self._desde = desde
        self._eventos: list[EventoDeDominio] = []

    def entregar(self, ahora: Minutos) -> None:
        if self._estatus is not EstatusDeVehiculo.DISPONIBLE:
            raise VehiculoNoDisponible()
        self._cambiar_a(EstatusDeVehiculo.RENTADO, ahora)

    def recibir_en_revision(self, ahora: Minutos) -> None:
        self._exigir(EstatusDeVehiculo.RENTADO)
        self._cambiar_a(EstatusDeVehiculo.EN_REVISION, ahora)

    def iniciar_limpieza(self, ahora: Minutos) -> None:
        self._exigir(EstatusDeVehiculo.EN_REVISION)
        self._cambiar_a(EstatusDeVehiculo.LIMPIEZA, ahora)

    def marcar_terminado(self, ahora: Minutos) -> None:
        """US11: la casilla 'Terminado' de Limpieza es la unica forma de quedar 'Disponible'."""
        self._exigir(EstatusDeVehiculo.LIMPIEZA)
        self._cambiar_a(EstatusDeVehiculo.DISPONIBLE, ahora)
        self._eventos.append(EventoDeDominio("VehiculoLiberado", self._id))

    def reportar_mantenimiento_mayor(self, ahora: Minutos, motivo: str = "", monto: Dinero | None = None) -> None:
        """US13: vestiduras o desodorizacion extrema. El monto es el del cargo retroactivo (S-9)."""
        self._exigir(EstatusDeVehiculo.LIMPIEZA)
        self._cambiar_a(EstatusDeVehiculo.MANTENIMIENTO_MAYOR, ahora)
        self._eventos.append(EventoDeDominio(
            "MantenimientoMayorRegistrado", self._id,
            {"motivo": motivo, "monto_centavos": (monto or Dinero()).centavos}))

    @property
    def id(self) -> Id:
        return self._id

    @property
    def placa(self) -> str:
        return self._placa

    @property
    def categoria(self) -> Categoria:
        return self._categoria

    @property
    def capacidad_tanque_litros(self) -> int:
        return self._capacidad_tanque_litros

    @property
    def estatus(self) -> EstatusDeVehiculo:
        return self._estatus

    @property
    def en_estatus_desde(self) -> Minutos:
        return self._desde

    def extraer_eventos(self) -> list[EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos

    def _exigir(self, esperado: EstatusDeVehiculo) -> None:
        if self._estatus is not esperado:
            raise TransicionDeEstatusInvalida()

    def _cambiar_a(self, nuevo: EstatusDeVehiculo, ahora: Minutos) -> None:
        self._estatus = nuevo
        self._desde = ahora
