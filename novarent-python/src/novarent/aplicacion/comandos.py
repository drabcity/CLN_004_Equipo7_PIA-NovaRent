"""Commands (CQRS): piden un cambio de estado. Devuelven lo minimo (normalmente un id)."""
from __future__ import annotations

from dataclasses import dataclass

from novarent.dominio import Id, InspeccionDeVehiculo, Minutos


@dataclass(frozen=True)
class EntregarVehiculo:  # CU-01
    reservacion_id: Id
    ultimos_4_tarjeta: str
    titular_tarjeta: str
    inspeccion_salida: InspeccionDeVehiculo


@dataclass(frozen=True)
class RegistrarDevolucion:  # CU-04
    contrato_id: Id
    inspeccion_devolucion: InspeccionDeVehiculo
    hora_devolucion: Minutos


@dataclass(frozen=True)
class MarcarVehiculoTerminado:  # CU-05
    vehiculo_id: Id
