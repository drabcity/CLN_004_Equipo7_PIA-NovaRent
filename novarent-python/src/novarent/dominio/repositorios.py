"""Interfaces de Repository: hablan en terminos del dominio, sin SQL.

Un Repository por Aggregate; solo devuelven raices completas. Las implementaciones viven en
infraestructura/.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .contrato_de_renta import ContratoDeRenta
from .comun import Id
from .reservacion import Reservacion
from .valores import Categoria
from .vehiculo import Vehiculo


class ReservacionRepository(ABC):
    @abstractmethod
    def obtener(self, reservacion_id: Id) -> Reservacion: ...

    @abstractmethod
    def guardar(self, reservacion: Reservacion) -> None: ...


class ContratoDeRentaRepository(ABC):
    @abstractmethod
    def obtener(self, contrato_id: Id) -> ContratoDeRenta: ...

    @abstractmethod
    def agregar(self, contrato: ContratoDeRenta) -> None: ...

    @abstractmethod
    def guardar(self, contrato: ContratoDeRenta) -> None: ...

    @abstractmethod
    def obtener_ultimo_de_vehiculo(self, vehiculo_id: Id) -> ContratoDeRenta:
        """US13: para agregar el cargo retroactivo al ultimo contrato del vehiculo."""


class VehiculoRepository(ABC):
    """Separado de DisponibilidadDeVehiculos por el principio I de SOLID: Limpieza no necesita buscar."""

    @abstractmethod
    def obtener(self, vehiculo_id: Id) -> Vehiculo: ...

    @abstractmethod
    def guardar(self, vehiculo: Vehiculo) -> None: ...


class DisponibilidadDeVehiculos(ABC):
    @abstractmethod
    def buscar_disponible_de_categoria(self, categoria: Categoria) -> Vehiculo | None: ...

    @abstractmethod
    def hay_disponibilidad_en(self, categoria: Categoria) -> bool: ...


class CatalogoDeCategorias(ABC):
    """Catalogo de solo lectura: jerarquia de categorias y sus tarifas."""

    @abstractmethod
    def superior_inmediata_de(self, categoria: Categoria) -> Categoria | None: ...

    @abstractmethod
    def inferior_inmediata_de(self, categoria: Categoria) -> Categoria | None: ...
