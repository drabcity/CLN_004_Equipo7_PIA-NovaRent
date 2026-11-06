"""Composition root: aqui (y solo aqui) se conectan los puertos con sus adaptadores."""
from __future__ import annotations

from dataclasses import dataclass

from novarent.aplicacion.consultas import (ConsultarOfertaDeCompensacionHandler, ConsultarPanelDeVehiculosHandler,
                                           ConsultarResumenDeCargosHandler)
from novarent.aplicacion.servicios import (ManejadorDeMantenimientoMayor, ServicioDeCompensacionDeCategoria,
                                           ServicioDeDevolucion, ServicioDeEntrega, ServicioDeLimpieza,
                                           ServicioDeValidacionDeDocumentacion)
from novarent.dominio import CalculadoraDeCargosExtra, CompensacionDeCategoria, Dinero
from .memoria import (Almacen, CatalogoEnMemoria, DisponibilidadEnMemoria, GeneradorSecuencial, LectorPanelEnMemoria,
                      LectorResumenCargosEnMemoria, PasarelaBancariaFalsa, PrecioDeCombustibleFijo, PublicadorEnMemoria,
                      RelojFijo, UnidadDeTrabajoEnMemoria)


@dataclass
class Aplicacion:
    almacen: Almacen
    reloj: RelojFijo
    banco: PasarelaBancariaFalsa
    publicador: PublicadorEnMemoria
    validacion: ServicioDeValidacionDeDocumentacion
    entrega: ServicioDeEntrega
    compensacion: ServicioDeCompensacionDeCategoria
    devolucion: ServicioDeDevolucion
    limpieza: ServicioDeLimpieza
    oferta: ConsultarOfertaDeCompensacionHandler
    panel: ConsultarPanelDeVehiculosHandler
    resumen_cargos: ConsultarResumenDeCargosHandler


def construir_en_memoria(precio_por_litro: Dinero = Dinero.pesos(25)) -> Aplicacion:
    almacen, reloj, banco, publicador = Almacen(), RelojFijo(), PasarelaBancariaFalsa(), PublicadorEnMemoria()
    uow = lambda: UnidadDeTrabajoEnMemoria(almacen, publicador)  # una UoW nueva por caso de uso
    disponibilidad, catalogo = DisponibilidadEnMemoria(almacen), CatalogoEnMemoria(almacen)
    compensacion = CompensacionDeCategoria(disponibilidad, catalogo)
    # Un repositorio de solo lectura para la Query de oferta (no necesita transaccion).
    lectura = UnidadDeTrabajoEnMemoria(almacen, publicador)
    publicador.suscribir("MantenimientoMayorRegistrado", ManejadorDeMantenimientoMayor(uow))
    return Aplicacion(
        almacen, reloj, banco, publicador,
        ServicioDeValidacionDeDocumentacion(uow, reloj),
        ServicioDeEntrega(uow, disponibilidad, banco, reloj, GeneradorSecuencial()),
        ServicioDeCompensacionDeCategoria(uow, compensacion),
        ServicioDeDevolucion(uow, PrecioDeCombustibleFijo(precio_por_litro), CalculadoraDeCargosExtra.estandar(), reloj),
        ServicioDeLimpieza(uow, reloj),
        ConsultarOfertaDeCompensacionHandler(lectura.reservaciones, compensacion),
        ConsultarPanelDeVehiculosHandler(LectorPanelEnMemoria(almacen)),
        ConsultarResumenDeCargosHandler(LectorResumenCargosEnMemoria(almacen)),
    )
