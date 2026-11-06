"""Entidad CargoExtra (dentro del Aggregate ContratoDeRenta)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .valores import Dinero


class TipoDeCargo(Enum):
    RETRASO = "Retraso"
    COMBUSTIBLE = "Combustible"
    KILOMETRAJE = "Kilometraje"
    DANOS = "Danos"
    MANTENIMIENTO_MAYOR = "Mantenimiento Mayor"


@dataclass
class CargoExtra:
    tipo: TipoDeCargo
    monto: Dinero
    descripcion: str
    cancelado: bool = False  # solo Administracion cancela cargos (US08, fuera de los 5 casos de uso)
