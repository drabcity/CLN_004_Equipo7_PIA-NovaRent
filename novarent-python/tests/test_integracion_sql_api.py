"""Pruebas de integracion HTTP + SQL sin modificar las 46 pruebas de Unidad 3.

En local usan SQLite temporal. En Docker/GitHub Actions pueden usar una DB de test
PostgreSQL aislada declarando NOVARENT_TEST_DATABASE_URL.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from novarent.api.main import crear_api
from novarent.dominio import Categoria, Dinero, Reservacion, Vehiculo, PeriodoDeRenta
from novarent.infraestructura.base_datos import Base, CategoriaFila, EventoPendienteFila, VehiculoFila, crear_motor
from novarent.infraestructura.cargar_csv import importar_csv
from novarent.infraestructura.contenedor_sql import construir_con_sql
from novarent.infraestructura.repositorios_sql import ConflictoDeConcurrencia
from novarent.infraestructura.unidad_de_trabajo_sql import UnidadDeTrabajoSql


@pytest.fixture
def url_db(tmp_path, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    url = os.getenv("NOVARENT_TEST_DATABASE_URL")
    if url:
        if not ("novarent_test" in url):
            raise AssertionError("NOVARENT_TEST_DATABASE_URL debe utilizar una base novarent_test separada")
        motor = crear_motor(url)
        Base.metadata.drop_all(motor)
        Base.metadata.create_all(motor)
        motor.dispose()
        return url
    return "sqlite:///" + str(tmp_path / "novarent_test.db")


@pytest.fixture
def cliente(url_db):
    with TestClient(crear_api(url_db, datos_demo=True)) as cliente:
        yield cliente


def inspeccion(km=1000, octavos=8, fotos=2, esquema=True):
    return {"kilometraje": km, "combustible_octavos": octavos,
            "fotografias": fotos, "esquema_completado": esquema, "marcas_de_dano": 0}


def validar(cliente, rid="res-demo-1", edad=30, verificada=True):
    r = cliente.get(f"/api/reservaciones/{rid}").json()
    ahora = r["inicio_minuto"]
    respuesta = cliente.post(f"/api/reservaciones/{rid}/documentacion", json={
        "titular_licencia": "Ana Perez", "edad": edad, "vigencia_licencia_minuto": ahora + 525600,
        "vigencia_identificacion_minuto": ahora + 525600, "identidad_verificada": verificada})
    return respuesta


def entregar(cliente, rid="res-demo-1", esquema=True):
    return cliente.post(f"/api/reservaciones/{rid}/entrega", json={
        "ultimos_4_tarjeta": "4242", "titular_tarjeta": "Ana Perez",
        "inspeccion_salida": inspeccion(esquema=esquema)})


def test_health_openapi_y_catalogo(cliente):
    assert cliente.get("/health").json()["estado"] == "ok"
    assert cliente.get("/api/categorias").json()[1]["nombre"] == "Compacta"
    esquema = cliente.get("/openapi.json").json()
    assert "/api/reservaciones/{reservacion_id}/entrega" in esquema["paths"]
    assert cliente.get("/docs").status_code == 200
    assert len(cliente.get("/api/vehiculos").json()) == 3


def test_importacion_idempotente_y_persistencia(url_db):
    app = construir_con_sql(url_db)
    assert importar_csv("data/ejemplo", app.sesiones, ahora=10000) == {
        "categorias": 3, "vehiculos": 3, "reservaciones": 2}
    assert importar_csv("data/ejemplo", app.sesiones, ahora=10000) == {
        "categorias": 0, "vehiculos": 0, "reservaciones": 0}
    with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow:
        assert uow.vehiculos.obtener("veh-com-1").estatus.value == "Disponible"
        assert uow.reservaciones.obtener("res-demo-1").periodo_pactado.fin_pactado == 12880
    app.motor.dispose()
    reapertura = construir_con_sql(url_db)
    assert reapertura.panel(None)[0].vehiculo_id == "veh-com-1"
    reapertura.motor.dispose()


def test_cu01_cu04_cu05_y_reportes(cliente):
    assert validar(cliente).json()["documentacion_valida"]
    respuesta = entregar(cliente)
    assert respuesta.status_code == 201, respuesta.text
    cid = respuesta.json()["contrato_id"]
    assert cliente.get("/api/reservaciones/res-demo-1").json()["estatus"] == "Entregada"
    panel = {v["vehiculo_id"]: v["estatus"] for v in cliente.get("/api/vehiculos").json()}
    assert panel["veh-com-1"] == "Rentado"
    ahora = cliente.get("/api/reservaciones/res-demo-1").json()["inicio_minuto"]
    respuesta = cliente.post(f"/api/contratos/{cid}/devolucion", json={
        "hora_devolucion_minuto": ahora + 2 * 1440 + 180,
        "inspeccion_devolucion": inspeccion(km=1700, octavos=6)})
    assert respuesta.status_code == 200, respuesta.text
    resumen = cliente.get(f"/api/contratos/{cid}/cargos").json()
    assert {x["tipo"] for x in resumen["lineas"]} == {"Retraso", "Combustible", "Kilometraje"}
    assert resumen["total"] == "$1581.25"
    inicio, fin = ahora, ahora + 3500
    cargos = cliente.get("/api/reportes/cargos-adicionales", params={"inicio_minuto": inicio, "fin_minuto": fin})
    assert cargos.json()["monto_cargos_no_cancelados_centavos"] == 158125
    uso = cliente.get("/api/reportes/utilizacion", params={"inicio_minuto": inicio, "fin_minuto": fin})
    assert uso.status_code == 200 and uso.json()["tasa_porcentaje"] > 0
    assert cliente.post("/api/vehiculos/veh-com-1/iniciar-limpieza").status_code == 200
    assert cliente.post("/api/vehiculos/veh-com-1/terminar").status_code == 200
    assert {v["vehiculo_id"]: v["estatus"] for v in cliente.get("/api/vehiculos").json()}["veh-com-1"] == "Disponible"


def test_documentacion_invalida_cancela_con_retencion(cliente):
    respuesta = validar(cliente, edad=16)
    assert respuesta.status_code == 200 and respuesta.json()["reservacion_cancelada"]
    r = cliente.get("/api/reservaciones/res-demo-1").json()
    assert r["retencion_centavos"] == 10000
    assert r["estatus"] == "Cancelada por documentacion invalida"
    assert entregar(cliente).status_code == 409


def test_entrega_invalida_no_deja_contrato_y_libera_autorizacion(cliente):
    assert validar(cliente).status_code == 200
    assert entregar(cliente, esquema=False).status_code == 409
    assert cliente.get("/api/reservaciones/res-demo-1").json()["estatus"] == "Confirmada"
    assert {v["vehiculo_id"]: v["estatus"] for v in cliente.get("/api/vehiculos").json()}["veh-com-1"] == "Disponible"
    assert cliente.app.state.servicios.banco.liberadas


def test_mantenimiento_retroactivo_post_commit(cliente):
    assert validar(cliente).status_code == 200
    cid = entregar(cliente).json()["contrato_id"]
    ahora = cliente.get("/api/reservaciones/res-demo-1").json()["inicio_minuto"]
    cliente.post(f"/api/contratos/{cid}/devolucion", json={
        "hora_devolucion_minuto": ahora + 1400, "inspeccion_devolucion": inspeccion(km=1100)})
    assert cliente.post("/api/vehiculos/veh-com-1/iniciar-limpieza").status_code == 200
    r = cliente.post("/api/vehiculos/veh-com-1/mantenimiento-mayor",
                      json={"motivo": "Lavado especial", "monto_centavos": 15000})
    assert r.status_code == 200, r.text
    resumen = cliente.get(f"/api/contratos/{cid}/cargos").json()
    assert any(x["tipo"] == "Mantenimiento Mayor" and x["monto"] == "$150.00" for x in resumen["lineas"])
    with cliente.app.state.servicios.sesiones() as s:
        eventos = s.scalars(select(EventoPendienteFila)).all()
        assert eventos and all(x.procesado for x in eventos)


def test_rollback_y_conflicto_version(url_db):
    app = construir_con_sql(url_db)
    importar_csv("data/ejemplo", app.sesiones, ahora=100)
    with pytest.raises(RuntimeError):
        with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow:
            vehiculo = uow.vehiculos.obtener("veh-com-1")
            vehiculo.entregar(100)
            uow.vehiculos.guardar(vehiculo)
            raise RuntimeError("error de DB simulado antes del commit")
    with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow:
        assert uow.vehiculos.obtener("veh-com-1").estatus.value == "Disponible"
    with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow_a:
        antiguo = uow_a.vehiculos.obtener("veh-com-1")
    with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow_b:
        actual = uow_b.vehiculos.obtener("veh-com-1")
        actual.entregar(101)
        uow_b.vehiculos.guardar(actual)
        uow_b.commit()
    with pytest.raises(ConflictoDeConcurrencia):
        with UnidadDeTrabajoSql(app.sesiones, app.publicador) as uow_c:
            antiguo.entregar(102)
            uow_c.vehiculos.guardar(antiguo)
            uow_c.commit()
    app.motor.dispose()


def test_errores_http_y_sin_credenciales(cliente, monkeypatch):
    assert cliente.get("/api/reservaciones/inexistente").status_code == 404
    assert cliente.get("/api/contratos/inexistente/cargos").status_code == 404
    assert cliente.post("/api/vehiculos/veh-com-1/terminar").status_code == 409
    assert cliente.get("/api/reportes/utilizacion", params={"inicio_minuto": 100, "fin_minuto": 90}).status_code == 400
    assert cliente.get("/api/reportes/cargos-adicionales", params={"inicio_minuto": 100, "fin_minuto": 90}).status_code == 400
    assert cliente.post("/api/reservaciones", json={"categoria": "NoExiste", "pago_inicial_centavos": 5000}).status_code == 404
    assert cliente.post("/api/reservaciones/res-demo-1/entrega", json={"ultimos_4_tarjeta": "12"}).status_code == 422
    monkeypatch.setenv("API_KEY", "clave-de-test")
    assert cliente.get("/api/vehiculos").status_code == 401
    assert cliente.get("/api/vehiculos", headers={"X-API-Key": "clave-de-test"}).status_code == 200
    assert cliente.get("/health").status_code == 200


def test_alta_reservacion_y_cu03_compensacion(cliente):
    creada = cliente.post("/api/reservaciones", json={"categoria": "Compacta", "pago_inicial_centavos": 30000,
                                                       "duracion_dias": 3})
    assert creada.status_code == 201, creada.text
    id_ = creada.json()["reservacion_id"]
    assert cliente.get(f"/api/reservaciones/{id_}").json()["estatus"] == "Confirmada"
    # Categoria Compacta disponible: US03 indica que la compensacion no aplica.
    assert cliente.post(f"/api/reservaciones/{id_}/compensacion", json={"acepta_upgrade": True}).status_code == 409
    assert cliente.get(f"/api/reservaciones/{id_}/oferta").status_code == 409


def test_reingreso_sin_seed(url_db):
    with TestClient(crear_api(url_db, datos_demo=False)) as c:
        assert c.get("/api/categorias").json() == []
        assert c.get("/api/vehiculos").json() == []


def test_upgrade_en_categoria_no_disponible(cliente):
    assert validar(cliente).status_code == 200
    assert entregar(cliente).status_code == 201  # ocupa la unica unidad Compacta
    creada = cliente.post("/api/reservaciones", json={"categoria": "Compacta", "pago_inicial_centavos": 30000,
                                                       "duracion_dias": 2})
    id_ = creada.json()["reservacion_id"]
    oferta = cliente.get(f"/api/reservaciones/{id_}/oferta")
    assert oferta.status_code == 200
    assert oferta.json()["tipo"] == "Upgrade"
    aplicada = cliente.post(f"/api/reservaciones/{id_}/compensacion", json={"acepta_upgrade": True})
    assert aplicada.status_code == 200 and aplicada.json()["categoria_destino"] == "SUV"
    assert cliente.get(f"/api/reservaciones/{id_}").json()["categoria"] == "SUV"
