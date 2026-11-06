"""Puertos de la capa de aplicacion: lo que los casos de uso necesitan del mundo exterior.

Los define la aplicacion y los implementa la infraestructura (principio D de SOLID).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from novarent.dominio import (ContratoDeRentaRepository, EventoDeDominio, Id, Minutos, ReservacionRepository,
                              VehiculoRepository, Dinero)


class UnidadDeTrabajo(ABC):
    """Una transaccion por caso de uso. Los eventos se publican DESPUES del commit (ADR-03).

    Uso:
        with fabrica() as uow:
            ...cambios con uow.reservaciones / uow.contratos / uow.vehiculos...
            uow.commit()
    Si el bloque termina sin commit o con una excepcion, se hace rollback automatico.
    """

    reservaciones: ReservacionRepository
    contratos: ContratoDeRentaRepository
    vehiculos: VehiculoRepository

    @abstractmethod
    def __enter__(self) -> "UnidadDeTrabajo": ...

    @abstractmethod
    def __exit__(self, tipo, valor, traza) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...


class PasarelaDeAutorizacionBancaria(ABC):
    """Banco: autorizacion del deposito en garantia (US12). Se pide ANTES de abrir la transaccion."""

    @abstractmethod
    def autorizar_deposito(self, ultimos_4: str, titular_tarjeta: str) -> str:
        """Devuelve el codigo de autorizacion."""

    @abstractmethod
    def liberar_autorizacion(self, codigo_autorizacion: str) -> None:
        """Compensacion: si la entrega falla despues de autorizar, se libera el deposito."""

    @abstractmethod
    def cobrar_cargos(self, codigo_autorizacion: str, monto: Dinero) -> None:
        """Cobro final de los cargos extra (por evento, despues del commit)."""


class ProveedorDePrecioDeCombustible(ABC):
    @abstractmethod
    def precio_por_litro_actual(self) -> Dinero: ...


class PublicadorDeEventos(ABC):
    @abstractmethod
    def publicar(self, evento: EventoDeDominio) -> None: ...


class Reloj(ABC):
    @abstractmethod
    def ahora(self) -> Minutos: ...


class GeneradorDeIds(ABC):
    @abstractmethod
    def nuevo(self, prefijo: str) -> Id: ...
