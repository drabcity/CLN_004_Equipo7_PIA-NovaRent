"""Composition root SQL; respeta los puertos de la Unidad 3."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from novarent.aplicacion.consultas import (ConsultarOfertaDeCompensacionHandler,
                                           ConsultarPanelDeVehiculosHandler, ConsultarResumenDeCargosHandler)
from novarent.aplicacion.puertos import GeneradorDeIds, Reloj
from novarent.aplicacion.servicios import (ManejadorDeMantenimientoMayor, ServicioDeCompensacionDeCategoria,
                                           ServicioDeDevolucion, ServicioDeEntrega, ServicioDeLimpieza,
                                           ServicioDeValidacionDeDocumentacion)
from novarent.dominio import CalculadoraDeCargosExtra, CompensacionDeCategoria, Dinero
from .base_datos import crear_fabrica_sesiones, crear_motor, inicializar_esquema
from .memoria import PasarelaBancariaFalsa, PrecioDeCombustibleFijo, PublicadorEnMemoria
from .repositorios_sql import (CatalogoSql, DisponibilidadSql, LectorPanelSql,
                                LectorResumenCargosSql, ReservacionRepositorioSql)
from .unidad_de_trabajo_sql import UnidadDeTrabajoSql


class RelojSistema(Reloj):
    def ahora(self) -> int:
        return int(time.time() // 60)  # minuto Unix en UTC, consistente en todos los servicios


class GeneradorUuid(GeneradorDeIds):
    def nuevo(self, prefijo: str) -> str:
        return f"{prefijo}-{uuid.uuid4().hex[:16]}"


@dataclass
class AplicacionSql:
    motor: object
    sesiones: object
    reloj: RelojSistema
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
    ids: GeneradorUuid


def construir_con_sql(database_url: str | None = None, inicializar: bool = True,
                      precio_por_litro: Dinero = Dinero.pesos(25)) -> AplicacionSql:
    motor = crear_motor(database_url)
    if inicializar:
        inicializar_esquema(motor)
    sesiones = crear_fabrica_sesiones(motor)
    reloj, banco, publicador, ids = RelojSistema(), PasarelaBancariaFalsa(), PublicadorEnMemoria(), GeneradorUuid()
    uow = lambda: UnidadDeTrabajoSql(sesiones, publicador)
    disponibilidad, catalogo = DisponibilidadSql(sesiones), CatalogoSql(sesiones)
    compensacion = CompensacionDeCategoria(disponibilidad, catalogo)
    # El handler abre una sesion dedicada cuando se ejecuta la Query, no la conserva entre peticiones.
    class LecturaReservaciones:
        def obtener(self, reservacion_id):
            with sesiones() as s:
                return ReservacionRepositorioSql(s, []).obtener(reservacion_id)
    publicador.suscribir("MantenimientoMayorRegistrado", ManejadorDeMantenimientoMayor(uow))
    return AplicacionSql(
        motor, sesiones, reloj, banco, publicador,
        ServicioDeValidacionDeDocumentacion(uow, reloj),
        ServicioDeEntrega(uow, disponibilidad, banco, reloj, ids),
        ServicioDeCompensacionDeCategoria(uow, compensacion),
        ServicioDeDevolucion(uow, PrecioDeCombustibleFijo(precio_por_litro), CalculadoraDeCargosExtra.estandar(), reloj),
        ServicioDeLimpieza(uow, reloj),
        ConsultarOfertaDeCompensacionHandler(LecturaReservaciones(), compensacion),
        ConsultarPanelDeVehiculosHandler(LectorPanelSql(sesiones)),
        ConsultarResumenDeCargosHandler(LectorResumenCargosSql(sesiones)),
        ids,
    )
