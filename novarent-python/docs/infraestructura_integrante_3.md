# Informe tecnico - Integrante 3: Infraestructura, API y calidad

## Punto de partida y alcance
Se partio del ZIP `novarent-arquitectura-python(2).zip`, preservando el dominio,
los servicios y los diagramas de U3. El nuevo trabajo reside fundamentalmente en
`infraestructura`, `api`, `tests`, CI/CD, Docker y documentacion. El caso abarca
CU-01 entrega, CU-02 documentacion, CU-03 compensacion, CU-04 devolucion y CU-05 limpieza.

## 1. Persistencia
Se implemento una base relacional mediante SQLAlchemy 2.x, compatible con
SQLite (local y pruebas) y PostgreSQL (Docker/produccion). Las tablas son:
`categorias`, `vehiculos`, `reservaciones`, `contratos`, `cargos_extra` y
`eventos_pendientes`. Las inspecciones son inmutables y se almacenan como
campos de salida/devolucion del contrato, sin repositorio independiente.

Los repositorios SQL aplican los puertos de U3; los modelos del dominio no
importan SQLAlchemy. Cada Aggregate se reconstituye con su historial relevante
(estatus, documentos, inspecciones, voucher y cargos). `UnidadDeTrabajoSql`
confirma la operacion completa; si existe error, hace rollback. El campo
`version` permite detectar modificaciones simultaneas con actualizaciones
condicionales, evitando que dos agentes reserven el mismo vehiculo.

La tabla `eventos_pendientes` conserva eventos para diagnostico y reproceso.
Tras commit se publican los eventos usando un publicador EN MEMORIA. El
manejador de Mantenimiento Mayor registra el cargo adicional en otra transaccion.
El reproceso es manual y actualmente la entrega de eventos puede repetirse si
un proceso falla despues de publicar y antes de marcar como procesado; para
produccion real debe introducirse idempotencia y procesamiento durable de outbox.

## 2. API REST
Se expone FastAPI con OpenAPI automatico (`/openapi.json`) y Swagger UI (`/docs`).
Los endpoints se corresponden con casos de uso y delegan a Application Services,
exceptuando la creacion de reservacion de apoyo a la demostracion y lectores
SQL de reportes. Los errores de dominio se devuelven como HTTP 409; registro
inexistente 404; datos invalidos 422; conflicto SQL 409.

El endpoint /health comprueba conectividad real con la DB.
Se puede configurar `API_KEY` para exigir encabezado `X-API-Key` a endpoints
funcionales. Cuando esta vacia, la API es accesible sin autenticacion; esto solo
se permite en una demostracion local aislada. No existen roles ni integracion
con un banco real: `PasarelaBancariaFalsa` simula autorizaciones.

## 3. Consultas
US14 tasa de utilizacion: implementacion de lectura propuesta como porcentaje
de minutos rentados durante la ventana dividido por la flota actual multiplicada
por la duracion. Los intervalos superpuestos para un mismo vehiculo se unifican.
**Validacion pendiente por Integrante 1**: la formula no esta detallada en los PDF
suministrados, y se excluyen periodos de limpieza y mantenimiento.

US15 cargos adicionales: suma cargos NO cancelados de contratos con devolucion
registrada en la ventana; los importes NO prueban que el banco los haya cobrado.
**Validacion pendiente** de la definicion de ingresos en el BRD definitivo.

## 4. Calidad, contenedores y despliegue
La nueva prueba `tests/test_integracion_sql_api.py` valida la API, persistencia,
reapertura de BD, rollback, version concurrente, compensacion, eventos,
consultas y reglas de negocio, conservando las 46 pruebas previas.
El workflow `.github/workflows/ci.yml` ejecutara pruebas SQLite con cobertura
>=80% y pruebas PostgreSQL al hacer push o PR. Este workflow solo estara
**activo y comprobable al subir el proyecto a GitHub**.

`docker-compose.yml` configura `db` (PostgreSQL), `app` (FastAPI), `tests`
(base separada `novarent_test`). Contiene volumen persistente, health checks
y variables de entorno. `render.yaml` es una plantilla de despliegue:
**no se afirma ningun despliegue real** sin vincular el repo y configurar DB/secretos.

## 5. Pendientes de integracion
- Incorporar los CSV oficiales, que no aparecian en los archivos proporcionados.
- Revisar campos y reglas con el trabajo final del Integrante 1 y el Integrante 2.
- Confirmar formulas de reportes US14/US15 y configuracion segura del despliegue.
- Resolver idempotencia de eventos, auth por roles, historiales y pago bancario real
  antes de cualquier utilizacion empresarial (fuera de la demo academica).
