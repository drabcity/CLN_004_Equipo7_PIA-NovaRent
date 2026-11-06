"""Unit of Work SQL: atomicidad para CU-01, CU-04 y demas comandos."""
from __future__ import annotations

import json
import logging
from sqlalchemy import select
from novarent.aplicacion.puertos import UnidadDeTrabajo
from novarent.dominio import EventoDeDominio
from .base_datos import EventoPendienteFila
from .repositorios_sql import ReservacionRepositorioSql, ContratoRepositorioSql, VehiculoRepositorioSql

log = logging.getLogger(__name__)


class UnidadDeTrabajoSql(UnidadDeTrabajo):
    def __init__(self, fabrica_sesiones, publicador):
        self._fabrica, self._publicador = fabrica_sesiones, publicador
        self._sesion = None
        self._eventos = []
        self._confirmada = False

    def __enter__(self):
        self._sesion = self._fabrica()
        self._eventos = []
        self._confirmada = False
        self.reservaciones = ReservacionRepositorioSql(self._sesion, self._eventos)
        self.contratos = ContratoRepositorioSql(self._sesion, self._eventos)
        self.vehiculos = VehiculoRepositorioSql(self._sesion, self._eventos)
        return self

    def __exit__(self, tipo, valor, traza):
        try:
            if not self._confirmada:
                self.rollback()
        finally:
            self._sesion.close()

    def commit(self):
        pendientes = [(evento, EventoPendienteFila(nombre=evento.nombre, agregado_id=evento.agregado_id,
                                                    datos_json=json.dumps(evento.datos))) for evento in self._eventos]
        try:
            for _, fila in pendientes:
                self._sesion.add(fila)
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise
        self._confirmada = True
        # ADR-03: solo despues de confirmar la transaccion SQL.
        for evento, fila in pendientes:
            try:
                self._publicador.publicar(evento)
                with self._fabrica.begin() as s:
                    db_fila = s.get(EventoPendienteFila, fila.id)
                    if db_fila:
                        db_fila.procesado = True
            except Exception:
                log.exception("Evento pendiente de reprocesar: %s (%s)", evento.nombre, fila.id)

    def rollback(self):
        if self._sesion is not None:
            self._sesion.rollback()
        self._eventos.clear()


def reprocesar_eventos_pendientes(fabrica_sesiones, publicador):
    """Reintenta eventos no entregados; ver limitacion de idempotencia en README."""
    with fabrica_sesiones() as s:
        pendientes = [(x.id, x.nombre, x.agregado_id, x.datos_json) for x in
                      s.scalars(select(EventoPendienteFila).where(EventoPendienteFila.procesado.is_(False))
                                .order_by(EventoPendienteFila.id)).all()]
    procesados = 0
    for evento_id, nombre, agregado_id, datos in pendientes:
        try:
            publicador.publicar(EventoDeDominio(nombre, agregado_id, json.loads(datos)))
            with fabrica_sesiones.begin() as s:
                fila = s.get(EventoPendienteFila, evento_id)
                if fila:
                    fila.procesado = True
            procesados += 1
        except Exception:
            log.exception("Fallo reprocesando evento pendiente %s", evento_id)
    return procesados
