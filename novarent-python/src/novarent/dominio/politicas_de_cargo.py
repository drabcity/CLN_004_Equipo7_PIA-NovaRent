"""Politicas de cargo (patron Strategy). Cada politica calcula UN tipo de cargo automatico (N3).

Agregar un cargo nuevo = agregar una politica, sin editar las existentes (principio O de SOLID).
Dano y Mantenimiento Mayor NO son politicas: no tienen regla de calculo (S-3, S-9) y por eso se
registran manualmente en el contrato (principio L de SOLID).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .cargo_extra import CargoExtra, TipoDeCargo
from .comun import Minutos
from .valores import Dinero, InspeccionDeVehiculo, PeriodoDeRenta, TarifaDiaria


@dataclass(frozen=True)
class ContextoDeDevolucion:
    tarifa_diaria: TarifaDiaria
    periodo: PeriodoDeRenta
    hora_devolucion: Minutos
    salida: InspeccionDeVehiculo
    devolucion: InspeccionDeVehiculo
    capacidad_tanque_litros: int
    precio_por_litro: Dinero


class PoliticaDeCargo(ABC):
    @abstractmethod
    def calcular(self, ctx: ContextoDeDevolucion) -> CargoExtra | None:
        """Devuelve el cargo, o None si la politica no aplica. Nunca lanza 'no implementado'."""


class CargoPorRetraso(PoliticaDeCargo):
    """US04, glosario #6 y #7.

    Supuesto S-11: las 4 horas se cuentan desde la hora pactada y la fraccion de hora se cobra completa.
    """

    TOLERANCIA_MINUTOS = 120
    LIMITE_DIA_COMPLETO_MINUTOS = 240

    def calcular(self, ctx: ContextoDeDevolucion) -> CargoExtra | None:
        retraso = ctx.hora_devolucion - ctx.periodo.fin_pactado
        if retraso <= self.TOLERANCIA_MINUTOS:
            return None
        if retraso > self.LIMITE_DIA_COMPLETO_MINUTOS:
            return CargoExtra(TipoDeCargo.RETRASO, ctx.tarifa_diaria, "Retraso de mas de 4 horas: se cobra el dia completo")
        horas = (retraso - self.TOLERANCIA_MINUTOS + 59) // 60
        return CargoExtra(TipoDeCargo.RETRASO, ctx.tarifa_diaria.porcentaje(20) * horas,
                          f"Retraso: {horas} h x 20% de la tarifa diaria")


class CargoPorCombustibleFaltante(PoliticaDeCargo):
    """US06, glosario #10 y #11: precio por litro de mercado + $100 MXN de servicio de recarga."""

    def calcular(self, ctx: ContextoDeDevolucion) -> CargoExtra | None:
        faltante = ctx.devolucion.combustible.faltante_respecto(ctx.salida.combustible)
        if faltante == 0:
            return None
        combustible = Dinero(ctx.precio_por_litro.centavos * ctx.capacidad_tanque_litros * faltante // 8)
        return CargoExtra(TipoDeCargo.COMBUSTIBLE, combustible + Dinero.pesos(100),
                          f"Combustible faltante: {faltante}/8 de tanque + $100 de servicio de recarga")


class CargoPorKilometrajeExcedente(PoliticaDeCargo):
    """US07, glosario #12 y #13: 250 km incluidos por dia, $5 MXN por km extra."""

    KM_INCLUIDOS_POR_DIA = 250

    def calcular(self, ctx: ContextoDeDevolucion) -> CargoExtra | None:
        recorrido = ctx.devolucion.kilometraje.valor - ctx.salida.kilometraje.valor
        excedente = recorrido - self.KM_INCLUIDOS_POR_DIA * ctx.periodo.dias()
        if excedente <= 0:
            return None
        return CargoExtra(TipoDeCargo.KILOMETRAJE, Dinero.pesos(5) * excedente,
                          f"Kilometraje excedente: {excedente} km x $5")


class CalculadoraDeCargosExtra:
    """Domain Service: aplica todas las politicas registradas."""

    def __init__(self, politicas: list[PoliticaDeCargo] | None = None) -> None:
        self._politicas = list(politicas or [])

    def agregar(self, politica: PoliticaDeCargo) -> None:
        self._politicas.append(politica)

    @staticmethod
    def estandar() -> "CalculadoraDeCargosExtra":
        return CalculadoraDeCargosExtra([CargoPorRetraso(), CargoPorCombustibleFaltante(), CargoPorKilometrajeExcedente()])

    def calcular(self, ctx: ContextoDeDevolucion) -> list[CargoExtra]:
        cargos = []
        for politica in self._politicas:
            cargo = politica.calcular(ctx)
            if cargo is not None:
                cargos.append(cargo)
        return cargos
