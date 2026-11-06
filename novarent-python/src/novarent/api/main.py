"""Ejecutar: uvicorn novarent.api.main:app --host 0.0.0.0 --port 8000

Swagger: /docs  |  OpenAPI JSON: /openapi.json
"""
from __future__ import annotations

import hmac
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from novarent.aplicacion.comandos import EntregarVehiculo, RegistrarDevolucion, MarcarVehiculoTerminado
from novarent.aplicacion.consultas import (ConsultarOfertaDeCompensacion,
                                           ConsultarPanelDeVehiculos, ConsultarResumenDeCargos)
from novarent.dominio import (Categoria, DecisionDelCliente, Dinero, DocumentacionConductor,
                              EntidadNoEncontrada, ErrorDeDominio, PeriodoDeRenta, Reservacion)
from novarent.dominio.reservacion import EstatusDeReservacion
from novarent.infraestructura.base_datos import CategoriaFila
from novarent.infraestructura.cargar_csv import importar_csv
from novarent.infraestructura.contenedor_sql import construir_con_sql
from novarent.infraestructura.reportes_sql import reporte_utilizacion, reporte_cargos_adicionales
from novarent.infraestructura.repositorios_sql import ConflictoDeConcurrencia
from .esquemas import (CompensacionEntrada, CrearReservacionEntrada, DocumentacionEntrada,
                       DevolucionEntrada, EntregaEntrada, MantenimientoEntrada)

logger = logging.getLogger(__name__)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verificar_api_key(clave: str | None = Security(api_key_header)) -> None:
    configurada = os.getenv("API_KEY")
    if configurada and (not clave or not hmac.compare_digest(clave, configurada)):
        raise HTTPException(status_code=401, detail="X-API-Key requerida o incorrecta")


def crear_api(database_url: str | None = None, datos_demo: bool | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(api: FastAPI):
        servicios = construir_con_sql(database_url)
        api.state.servicios = servicios
        cargar_demo = (os.getenv("NOVARENT_SEED_DEMO", "false").lower() == "true") if datos_demo is None else datos_demo
        if cargar_demo:
            importar_csv("data/ejemplo", servicios.sesiones)
        try:
            yield
        finally:
            servicios.motor.dispose()

    api = FastAPI(title="NovaRent - PIA Componentes de Logica de Negocio", version="1.0.0",
                  description=("API REST de entrega, devolucion y liberacion de vehiculos. "
                               "Los pagos bancarios son simulados, NO procesan dinero real. "
                               "Los instantes se representan en minutos Unix (UTC)."), lifespan=lifespan)

    @api.exception_handler(EntidadNoEncontrada)
    async def _no_encontrada(_request, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @api.exception_handler(ConflictoDeConcurrencia)
    async def _conflicto_concurrencia(_request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @api.exception_handler(ErrorDeDominio)
    async def _error_negocio(_request, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @api.exception_handler(IntegrityError)
    async def _error_integridad(_request, exc):
        logger.warning("Restriccion de integridad SQL: %s", exc)
        return JSONResponse(status_code=409, content={"detail": "Conflicto de integridad en la base de datos"})

    @api.exception_handler(ValueError)
    async def _valor(_request, exc):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @api.get("/health", tags=["Operacion"])
    def health():
        # Health check para Docker: no necesita cargar informacion personal.
        try:
            from sqlalchemy import text
            with api.state.servicios.motor.connect() as conn:
                conn.execute(text("SELECT 1"))
        except OperationalError:
            raise HTTPException(status_code=503, detail="Base de datos no disponible")
        return {"estado": "ok", "base_de_datos": "disponible"}

    @api.get("/api/categorias", dependencies=[Depends(verificar_api_key)], tags=["Consultas"])
    def categorias():
        with api.state.servicios.sesiones() as s:
            return [{"nombre": x.nombre, "nivel": x.nivel, "tarifa_centavos": x.tarifa_centavos}
                    for x in s.scalars(select(CategoriaFila).order_by(CategoriaFila.nivel)).all()]

    @api.get("/api/vehiculos", dependencies=[Depends(verificar_api_key)], tags=["Consultas"])
    def panel():
        return [asdict(v) for v in api.state.servicios.panel(ConsultarPanelDeVehiculos())]

    @api.post("/api/reservaciones", status_code=201, dependencies=[Depends(verificar_api_key)], tags=["Reservaciones"])
    def crear_reservacion(entrada: CrearReservacionEntrada):
        """Alta de demostracion para poder ejecutar CU-01; requiere categoria de CSV."""
        app = api.state.servicios
        with app.sesiones() as s:
            c = s.get(CategoriaFila, entrada.categoria)
            if c is None:
                raise EntidadNoEncontrada(f"Categoria {entrada.categoria} no existe")
            categoria = Categoria(c.nombre, c.nivel, Dinero(c.tarifa_centavos))
        ahora = app.reloj.ahora()
        r = Reservacion(app.ids.nuevo("res"), categoria, Dinero(entrada.pago_inicial_centavos),
                       PeriodoDeRenta(ahora, ahora + entrada.duracion_dias * 1440))
        from novarent.infraestructura.unidad_de_trabajo_sql import UnidadDeTrabajoSql
        with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow:
            uow.reservaciones.guardar(r)
            uow.commit()
        return {"reservacion_id": r.id, "estatus": r.estatus.value}

    @api.get("/api/reservaciones/{reservacion_id}", dependencies=[Depends(verificar_api_key)], tags=["Reservaciones"])
    def consultar_reservacion(reservacion_id: str):
        from novarent.infraestructura.unidad_de_trabajo_sql import UnidadDeTrabajoSql
        app = api.state.servicios
        with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow:
            r = uow.reservaciones.obtener(reservacion_id)
            return {"id": r.id, "categoria": r.categoria.nombre, "tarifa_diaria_centavos": r.tarifa_diaria.centavos,
                    "estatus": r.estatus.value, "pago_inicial_centavos": r.pago_inicial.centavos,
                    "retencion_centavos": r.retencion.centavos,
                    "inicio_minuto": r.periodo_pactado.inicio, "fin_pactado_minuto": r.periodo_pactado.fin_pactado}

    @api.post("/api/reservaciones/{reservacion_id}/documentacion", dependencies=[Depends(verificar_api_key)], tags=["CU-02"])
    def validar_documentacion(reservacion_id: str, entrada: DocumentacionEntrada):
        doc = DocumentacionConductor(entrada.titular_licencia, entrada.edad,
                 entrada.vigencia_licencia_minuto, entrada.vigencia_identificacion_minuto, entrada.identidad_verificada)
        valida = api.state.servicios.validacion.validar_documentacion_del_conductor(reservacion_id, doc)
        return {"documentacion_valida": valida, "reservacion_cancelada": not valida}

    @api.get("/api/reservaciones/{reservacion_id}/oferta", dependencies=[Depends(verificar_api_key)], tags=["CU-03"])
    def consultar_oferta(reservacion_id: str):
        return asdict(api.state.servicios.oferta(ConsultarOfertaDeCompensacion(reservacion_id)))

    @api.post("/api/reservaciones/{reservacion_id}/compensacion", dependencies=[Depends(verificar_api_key)], tags=["CU-03"])
    def aplicar_compensacion(reservacion_id: str, entrada: CompensacionEntrada):
        oferta = api.state.servicios.compensacion.resolver_categoria_no_disponible(
                    reservacion_id, DecisionDelCliente(entrada.acepta_upgrade, entrada.acepta_downgrade))
        return {"tipo": oferta.tipo.value, "categoria_destino": oferta.categoria_destino.nombre if oferta.categoria_destino else None,
                "descuento_porcentaje": oferta.descuento_porcentaje, "tarifa_resultante_centavos": oferta.tarifa_resultante.centavos}

    @api.post("/api/reservaciones/{reservacion_id}/entrega", status_code=201,
              dependencies=[Depends(verificar_api_key)], tags=["CU-01"])
    def entregar(reservacion_id: str, entrada: EntregaEntrada):
        cmd = EntregarVehiculo(reservacion_id, entrada.ultimos_4_tarjeta, entrada.titular_tarjeta,
                               entrada.inspeccion_salida.al_dominio())
        return {"contrato_id": api.state.servicios.entrega.entregar_vehiculo(cmd)}

    @api.post("/api/contratos/{contrato_id}/devolucion", dependencies=[Depends(verificar_api_key)], tags=["CU-04"])
    def devolver(contrato_id: str, entrada: DevolucionEntrada):
        cmd = RegistrarDevolucion(contrato_id, entrada.inspeccion_devolucion.al_dominio(), entrada.hora_devolucion_minuto)
        return {"contrato_id": api.state.servicios.devolucion.registrar_devolucion(cmd)}

    @api.get("/api/contratos/{contrato_id}/cargos", dependencies=[Depends(verificar_api_key)], tags=["CU-04"])
    def resumen_cargos(contrato_id: str):
        return asdict(api.state.servicios.resumen_cargos(ConsultarResumenDeCargos(contrato_id)))

    @api.post("/api/vehiculos/{vehiculo_id}/iniciar-limpieza", dependencies=[Depends(verificar_api_key)], tags=["CU-05"])
    def iniciar_limpieza(vehiculo_id: str):
        api.state.servicios.limpieza.iniciar_limpieza(vehiculo_id)
        return {"vehiculo_id": vehiculo_id, "estatus": "Limpieza"}

    @api.post("/api/vehiculos/{vehiculo_id}/terminar", dependencies=[Depends(verificar_api_key)], tags=["CU-05"])
    def marcar_terminado(vehiculo_id: str):
        api.state.servicios.limpieza.marcar_terminado(MarcarVehiculoTerminado(vehiculo_id))
        return {"vehiculo_id": vehiculo_id, "estatus": "Disponible"}

    @api.post("/api/vehiculos/{vehiculo_id}/mantenimiento-mayor", dependencies=[Depends(verificar_api_key)], tags=["CU-05"])
    def mantenimiento_mayor(vehiculo_id: str, entrada: MantenimientoEntrada):
        api.state.servicios.limpieza.reportar_mantenimiento_mayor(vehiculo_id, entrada.motivo, Dinero(entrada.monto_centavos))
        return {"vehiculo_id": vehiculo_id, "estatus": "Mantenimiento Mayor"}

    @api.get("/api/reportes/utilizacion", dependencies=[Depends(verificar_api_key)], tags=["Reportes US14"])
    def utilizacion(inicio_minuto: int = Query(ge=0), fin_minuto: int = Query(ge=0)):
        app = api.state.servicios
        return reporte_utilizacion(app.sesiones, inicio_minuto, fin_minuto, app.reloj.ahora())

    @api.get("/api/reportes/cargos-adicionales", dependencies=[Depends(verificar_api_key)], tags=["Reportes US15"])
    def ingresos_por_cargos(inicio_minuto: int = Query(ge=0), fin_minuto: int = Query(ge=0)):
        return reporte_cargos_adicionales(api.state.servicios.sesiones, inicio_minuto, fin_minuto)

    return api


app = crear_api()
