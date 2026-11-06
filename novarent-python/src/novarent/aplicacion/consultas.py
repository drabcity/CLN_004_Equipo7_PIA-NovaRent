"""Queries (CQRS): responden una pregunta y NUNCA cambian el estado. Devuelven DTOs, no Aggregates."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from novarent.dominio import CompensacionDeCategoria, Id, ReservacionRepository


@dataclass(frozen=True)
class OfertaDeCompensacionDto:
    tipo: str
    categoria_destino: str | None
    descuento_porcentaje: int
    tarifa_diaria: str


@dataclass(frozen=True)
class PanelVehiculoDto:
    vehiculo_id: str
    placa: str
    categoria: str
    estatus: str
    en_estatus_desde: int


@dataclass(frozen=True)
class LineaDeCargoDto:
    tipo: str
    descripcion: str
    monto: str
    cancelado: bool


@dataclass(frozen=True)
class ResumenDeCargosDto:
    contrato_id: str
    lineas: tuple[LineaDeCargoDto, ...]
    total: str


class LectorDePanelDeVehiculos(ABC):
    @abstractmethod
    def leer(self) -> list[PanelVehiculoDto]: ...


class LectorDeResumenDeCargos(ABC):
    @abstractmethod
    def leer(self, contrato_id: Id) -> ResumenDeCargosDto: ...


@dataclass(frozen=True)
class ConsultarOfertaDeCompensacion:
    reservacion_id: Id


@dataclass(frozen=True)
class ConsultarPanelDeVehiculos:
    pass


@dataclass(frozen=True)
class ConsultarResumenDeCargos:
    contrato_id: Id


class ConsultarOfertaDeCompensacionHandler:
    """CU-03: el Agente ve la oferta antes de que el cliente decida (US03)."""

    def __init__(self, reservaciones: ReservacionRepository, compensacion: CompensacionDeCategoria) -> None:
        self._reservaciones, self._compensacion = reservaciones, compensacion

    def __call__(self, q: ConsultarOfertaDeCompensacion) -> OfertaDeCompensacionDto:
        reservacion = self._reservaciones.obtener(q.reservacion_id)
        oferta = self._compensacion.proponer(reservacion.categoria)
        destino = oferta.categoria_destino.nombre if oferta.categoria_destino else None
        return OfertaDeCompensacionDto(oferta.tipo.value, destino, oferta.descuento_porcentaje, str(oferta.tarifa_resultante))


class ConsultarPanelDeVehiculosHandler:
    """CU-05 (US11): estatus de todos los vehiculos para el personal de patio."""

    def __init__(self, lector: LectorDePanelDeVehiculos) -> None:
        self._lector = lector

    def __call__(self, q: ConsultarPanelDeVehiculos) -> list[PanelVehiculoDto]:
        return self._lector.leer()


class ConsultarResumenDeCargosHandler:
    """CU-04: desglose de cargos para el cliente (ataca las disputas por cobros del BRD)."""

    def __init__(self, lector: LectorDeResumenDeCargos) -> None:
        self._lector = lector

    def __call__(self, q: ConsultarResumenDeCargos) -> ResumenDeCargosDto:
        return self._lector.leer(q.contrato_id)
