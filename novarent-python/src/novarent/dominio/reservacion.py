"""Aggregate Reservacion (glosario #1). Raiz: Reservacion.

Invariantes: no se entrega con documentacion invalida; al cancelar por documentacion invalida se
retiene el 10% del pago inicial; una reservacion cancelada o entregada ya no cambia.
"""
from __future__ import annotations

from enum import Enum

from .comun import DocumentacionInvalida, EventoDeDominio, Id, Minutos, ReservacionNoVigente
from .valores import (
    Categoria,
    DocumentacionConductor,
    Dinero,
    OfertaDeCompensacion,
    PeriodoDeRenta,
    TipoDeCompensacion,
)


class EstatusDeReservacion(Enum):
    CONFIRMADA = "Confirmada"
    ENTREGADA = "Entregada"
    CANCELADA_POR_DOCUMENTACION_INVALIDA = "Cancelada por documentacion invalida"
    CANCELADA_POR_CATEGORIA_NO_DISPONIBLE = "Cancelada por categoria no disponible"


class Reservacion:
    def __init__(self, id: Id, categoria_reservada: Categoria, pago_inicial: Dinero, periodo_pactado: PeriodoDeRenta) -> None:
        self._id = id
        self._categoria = categoria_reservada
        self._tarifa_diaria = categoria_reservada.tarifa_diaria
        self._pago_inicial = pago_inicial
        self._periodo = periodo_pactado
        self._estatus = EstatusDeReservacion.CONFIRMADA
        self._retencion = Dinero()
        self._documentacion: DocumentacionConductor | None = None
        self._eventos: list[EventoDeDominio] = []

    # ---- comportamiento
    def validar_documentacion(self, documentacion: DocumentacionConductor, ahora: Minutos) -> None:
        """US10: si no es valida se lanza DocumentacionInvalida (la reservacion queda confirmada)."""
        self._exigir_confirmada()
        self._documentacion = documentacion
        if not documentacion.es_valida(ahora):
            raise DocumentacionInvalida()

    def cancelar_por_documentacion_invalida(self) -> None:
        """US10: estatus 'Documentacion invalida' y retencion del 10% del pago inicial."""
        self._exigir_confirmada()
        self._estatus = EstatusDeReservacion.CANCELADA_POR_DOCUMENTACION_INVALIDA
        self._retencion = self._pago_inicial.porcentaje(10)
        self._eventos.append(EventoDeDominio("DocumentacionInvalidaRegistrada", self._id))

    def aplicar_compensacion(self, oferta: OfertaDeCompensacion) -> None:
        """US03: upgrade (misma tarifa) o downgrade (tarifa con 20% de descuento)."""
        self._exigir_confirmada()
        if oferta.tipo is TipoDeCompensacion.NINGUNA or oferta.categoria_destino is None:
            raise ValueError("No hay compensacion que aplicar")
        self._categoria = oferta.categoria_destino
        self._tarifa_diaria = oferta.tarifa_resultante
        self._eventos.append(EventoDeDominio("CategoriaCompensada", self._id))

    def cancelar_por_categoria_no_disponible(self) -> None:
        self._exigir_confirmada()
        self._estatus = EstatusDeReservacion.CANCELADA_POR_CATEGORIA_NO_DISPONIBLE

    def marcar_entregada(self, ahora: Minutos) -> None:
        self._exigir_confirmada()
        if self._documentacion is None or not self._documentacion.es_valida(ahora):
            raise DocumentacionInvalida()
        self._estatus = EstatusDeReservacion.ENTREGADA

    # ---- consultas
    @property
    def id(self) -> Id:
        return self._id

    @property
    def categoria(self) -> Categoria:
        return self._categoria

    @property
    def tarifa_diaria(self) -> Dinero:
        return self._tarifa_diaria

    @property
    def pago_inicial(self) -> Dinero:
        return self._pago_inicial

    @property
    def retencion(self) -> Dinero:
        return self._retencion

    @property
    def periodo_pactado(self) -> PeriodoDeRenta:
        return self._periodo

    @property
    def estatus(self) -> EstatusDeReservacion:
        return self._estatus

    @property
    def titular_licencia(self) -> str:
        if self._documentacion is None:
            raise DocumentacionInvalida()
        return self._documentacion.titular_licencia

    def extraer_eventos(self) -> list[EventoDeDominio]:
        eventos, self._eventos = self._eventos, []
        return eventos

    def _exigir_confirmada(self) -> None:
        if self._estatus is not EstatusDeReservacion.CONFIRMADA:
            raise ReservacionNoVigente()
