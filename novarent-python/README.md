# NovaRent - PIA Componentes de Logica de Negocio (UANL/FIME)

Implementacion funcional del sistema de renta de autos **NovaRent** a partir de la
arquitectura y casos de uso de U3. Esta version incorpora la parte del **Integrante 3:
Infraestructura, API y calidad**, sin eliminar las clases originales de Dominio y
Application. Se conservaron el informe y diagramas U3 originales.

**Estado comprobado:** API REST y persistencia SQLite funcionan localmente y las
pruebas de integracion del proyecto fueron ejecutadas. El despliegue publico y el
pipeline remoto requieren acciones en las cuentas del equipo; NO estan realizados
por el mero hecho de incluir configuraciones.

## 1. Ejecutar sin Docker (recomendado para iniciar)

Requisitos: Python 3.10+ y terminal en la carpeta `novarent-python/`.

En Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m novarent.infraestructura.cargar_csv --directorio data/ejemplo
uvicorn novarent.api.main:app --reload
```

En Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m novarent.infraestructura.cargar_csv --directorio data/ejemplo
uvicorn novarent.api.main:app --reload
```

Acceder a **http://localhost:8000/docs** (Swagger), ver vehiculos y ejecutar los
casos de uso. Por defecto la base es SQLite local `novarent.db`. No mezclar el
archivo de base de datos con el codigo que se suba a GitHub.

`python run_tests.py` conserva las pruebas originales sin dependencias externas,
aunque la nueva API requiere FastAPI/SQLAlchemy.

## 2. Ejecutar con Docker (DB + App + Tests)

Instalar Docker Desktop y abrir terminal en la carpeta principal:

```bash
cp .env.example .env                  # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

- API y Swagger: http://localhost:8000/docs
- PostgreSQL: localhost:5432 (configurable en `.env`)
- Datos de ejemplo: se cargan automaticamente cuando `NOVARENT_SEED_DEMO=true`

Para ejecutar **las pruebas contra PostgreSQL aislado**:

```bash
docker compose --profile tests run --rm tests
```

Para apagar sin borrar los datos: `docker compose down`. Para borrar volumen
de prueba/produccion local: `docker compose down -v` (DESTRUYE LOS DATOS).

> Si se creo el volumen PostgreSQL antes de agregar `novarent_test`, puede que
> dicha base no exista; crearla manualmente con `docker compose exec db psql -U
> novarent -d novarent -c 'CREATE DATABASE novarent_test'` o reiniciar el
> volumen de pruebas con cuidado. La creacion automatica solo corre en un
> volumen vacio.

## 3. Pruebas y cobertura

```bash
pytest -q
pytest -q --cov=novarent --cov-report=term-missing --cov-fail-under=80
```

Se incluyen pruebas originales de dominio y nuevas pruebas HTTP/SQL que validan
CU-01 a CU-05, atomicidad, concurrencia, consultas y CSV. El minimo de cobertura
del PIA es 80%; los resultados de la ejecucion local estan en
`docs/evidencias/pruebas_locales.txt`.

## 4. Probar la demostracion completa

1. Ir a `/docs`, GET `/api/vehiculos`: verificar `veh-com-1` disponible.
2. GET `/api/reservaciones/res-demo-1` para obtener `inicio_minuto`.
3. POST `/api/reservaciones/res-demo-1/documentacion`: titular `Ana Perez`,
   edad 30, identidad verificada, vigencias mayores a `inicio_minuto`.
4. POST `/api/reservaciones/res-demo-1/entrega`: `ultimos_4_tarjeta=4242`,
   `titular_tarjeta=Ana Perez`, km 1000, gasolina 8 octavos, esquema true y 2 fotos.
5. Copiar el `contrato_id` devuelto. GET `/api/vehiculos`: ya esta `Rentado`.
6. POST `/api/contratos/{contrato_id}/devolucion`: `hora_devolucion_minuto`
   igual a `inicio_minuto + 3060`; km 1700 y gasolina 6 octavos.
7. GET `/api/contratos/{contrato_id}/cargos`: retraso, combustible y kilometraje.
8. POST `/api/vehiculos/veh-com-1/iniciar-limpieza` y luego `/terminar`.
9. GET `/api/vehiculos`: regreso a Disponible.
10. Consultar `/api/reportes/cargos-adicionales` en el intervalo correspondiente.

Ver `docs/api/README.md` para cuerpos JSON listos para copiar. El banco es
**simulado**, sin cargos reales. Los datos son ficticios.

## 5. Arquitectura y estructura

```text
src/novarent/
  dominio/          # Entidades, reglas, State Machine, puertos Repository (U3)
  aplicacion/       # Commands, Queries y servicios de negocio (U3)
  infraestructura/  # SQLite/PostgreSQL, Unit of Work, CSV, reportes y adaptadores
  api/              # FastAPI, rutas y esquemas HTTP

tests/              # 46 pruebas U3 + pruebas de integracion SQL/API
.github/workflows/ci.yml  # CI/CD al subir a GitHub
docker-compose.yml  # db + app + tests
Dockerfile
render.yaml         # plantilla despliegue no ejecutado
.env.example        # configuracion sin secretos
docs/api/openapi.json
```

Flujo: Cliente HTTP -> FastAPI -> Application Services -> Domain ->
Repository/Unit of Work SQL -> PostgreSQL. Eventos despues del commit, con
registro en `eventos_pendientes`. Se mantiene la variante en memoria U3 para
pruebas puramente de dominio.

Documentacion detallada: `docs/infraestructura_integrante_3.md`.

## 6. GitHub Actions y despliegue

El workflow de `.github/workflows/ci.yml` corre al hacer push a `main`/`master`
y al crear PR: instala dependencias, exige >=80% de cobertura con SQLite,
repite pruebas de integracion contra PostgreSQL y valida Docker Compose.
Solo se puede comprobar el estado del workflow **despues de subir el repo**.

Para publicar la API, se incluye `render.yaml`. Es necesario:

1. Subir el repo a GitHub, crear servicio web en Render y conectarlo.
2. Proporcionar una base PostgreSQL externa y definir `DATABASE_URL` con formato
   `postgresql+psycopg://usuario:clave@host:5432/base` (usar URL interna si aplica).
3. Definir una `API_KEY` fuerte en la plataforma, no en GitHub.
4. Verificar `/health`, `/docs` y un flujo CU-01..CU-05 en la URL publica.
5. Añadir la URL real de la API y del repositorio en el reporte final.

Para una demo publica se recomienda autenticar tambien Swagger y restringir
origenes; la API actual es una base academica, no un sistema de pagos en produccion.

## 7. Dependencias y puntos por acordar con el equipo

- **Integrante 1:** revisar formulas y criterios US14/US15, endpoints, trazabilidad.
- **Integrante 2:** mantener invariantes de negocio y acordar el modelo final.
- **Datos oficiales:** el ZIP original NO contiene CSV; `data/ejemplo` es ficticio.
- **Cobros bancarios:** solo existe el fake incluido en U3; pagos y retenciones
  no se ejecutan con bancos reales.
- **Pendiente antes de produccion real:** autenticacion por roles, cifrado,
  migraciones (Alembic), idempotencia de outbox y observabilidad avanzada.

Para validar la correspondencia con BRD/Unidad 3 ver `docs/trazabilidad.md`,
`docs/supuestos.md` y `docs/Actividad_Unidad_3_NovaRent.docx`.
