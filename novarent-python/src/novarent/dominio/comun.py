"""Tipos basicos y errores del dominio de NovaRent.

Los nombres de los errores salen del glosario y de las historias de usuario (Unidad 2).
"""
from __future__ import annotations

from dataclasses import dataclass, field

Id = str
# Instante o duracion en minutos. Simplificacion para el ejemplo.
Minutos = int


class ErrorDeDominio(Exception):
    """Base de todas las reglas de negocio que se violan."""


class DocumentacionInvalida(ErrorDeDominio):  # Glosario #16 (US10)
    def __init__(self) -> None:
        super().__init__("Documentacion invalida")


class VehiculoNoDisponible(ErrorDeDominio):  # N2: solo un vehiculo "Disponible" puede entregarse
    def __init__(self) -> None:
        super().__init__("Vehiculo no disponible")


class EsquemaDeDanosIncompleto(ErrorDeDominio):  # US05
    def __init__(self) -> None:
        super().__init__("Esquema de danos incompleto: se requiere el esquema y al menos una fotografia")


class TransicionDeEstatusInvalida(ErrorDeDominio):  # Glosario #17
    def __init__(self) -> None:
        super().__init__("Transicion de estatus invalida")


class ContratoYaDevuelto(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("El contrato ya fue devuelto")


class ReservacionNoVigente(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("La reservacion no esta vigente")


class VoucherInvalido(ErrorDeDominio):  # US12
    def __init__(self, motivo: str) -> None:
        super().__init__(f"Voucher invalido: {motivo}")


class CompensacionNoAplica(ErrorDeDominio):  # US03
    def __init__(self) -> None:
        super().__init__("La categoria reservada si tiene disponibilidad")


class EntidadNoEncontrada(ErrorDeDominio):
    pass


@dataclass(frozen=True)
class EventoDeDominio:
    """Algo que ya ocurrio en el negocio (ver mapa de dominio)."""

    nombre: str
    agregado_id: Id
    datos: dict = field(default_factory=dict, compare=False)
