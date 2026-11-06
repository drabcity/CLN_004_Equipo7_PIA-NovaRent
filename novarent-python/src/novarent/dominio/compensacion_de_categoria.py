"""Domain Service: decide upgrade o downgrade cuando la categoria reservada no tiene unidades.

(US03, N4, glosario #3, #4, #5). Involucra la reservacion, la jerarquia y la disponibilidad, por eso
no pertenece a una sola entidad. Supuesto: el 20% de descuento se aplica a la tarifa de la categoria
inferior (hallazgo de la Etapa 1).
"""
from __future__ import annotations

from .comun import CompensacionNoAplica
from .repositorios import CatalogoDeCategorias, DisponibilidadDeVehiculos
from .valores import Categoria, DecisionDelCliente, OfertaDeCompensacion, TipoDeCompensacion


class CompensacionDeCategoria:
    def __init__(self, disponibilidad: DisponibilidadDeVehiculos, catalogo: CatalogoDeCategorias) -> None:
        self._disponibilidad = disponibilidad
        self._catalogo = catalogo

    def proponer(self, reservada: Categoria, omitir_upgrade: bool = False) -> OfertaDeCompensacion:
        """Primera oferta al cliente: upgrade si existe, si no downgrade."""
        if self._disponibilidad.hay_disponibilidad_en(reservada):
            raise CompensacionNoAplica()
        if not omitir_upgrade:
            superior = self._catalogo.superior_inmediata_de(reservada)
            if superior is not None and self._disponibilidad.hay_disponibilidad_en(superior):
                # Upgrade gratuito: la tarifa sigue siendo la de la categoria reservada.
                return OfertaDeCompensacion(TipoDeCompensacion.UPGRADE, superior, 0, reservada.tarifa_diaria)
        inferior = self._catalogo.inferior_inmediata_de(reservada)
        if inferior is not None and self._disponibilidad.hay_disponibilidad_en(inferior):
            tarifa = inferior.tarifa_diaria
            return OfertaDeCompensacion(TipoDeCompensacion.DOWNGRADE, inferior, 20, tarifa - tarifa.porcentaje(20))
        return OfertaDeCompensacion()

    def resolver(self, reservada: Categoria, decision: DecisionDelCliente) -> OfertaDeCompensacion:
        """Resultado final segun lo que decide el cliente (BPMN: acepta upgrade / acepta categoria inferior)."""
        oferta = self.proponer(reservada)
        if oferta.tipo is TipoDeCompensacion.UPGRADE:
            if decision.acepta_upgrade:
                return oferta
            oferta = self.proponer(reservada, omitir_upgrade=True)
        if oferta.tipo is TipoDeCompensacion.DOWNGRADE and decision.acepta_downgrade:
            return oferta
        return OfertaDeCompensacion()
