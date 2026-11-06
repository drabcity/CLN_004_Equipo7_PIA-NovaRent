# Diagrama de arquitectura de infraestructura - PIA

Diagrama de despliegue y capas compatible con el codigo (sugerido para
integrar en los diagramas UML del Integrante 1).

```mermaid
flowchart TD
    Client[Cliente / Swagger UI] --> API[FastAPI - src/novarent/api]
    API --> APP[Application Services - U3]
    APP --> DOMAIN[DDD / State Machine - U3]
    APP --> PORTS[Repository + Unit of Work - Puertos U3]
    PORTS --> ADAPTER[Repositorios SQL + UnitOfWork SQL]
    ADAPTER --> DB[(PostgreSQL / SQLite)]
    ADAPTER --> OUTBOX[(eventos_pendientes)]
    API --> REPORTS[Lectores SQL - reportes US14/US15]
    REPORTS --> DB
    OUTBOX --> PUB[Publicador en memoria / proceso de eventos]
    PUB --> HANDLER[Manejador Mantenimiento Mayor]
    HANDLER --> PORTS
    GHA[GitHub Actions] --> TESTS[Pruebas + coverage 80%]
    TESTS --> DB
    DOCKER[Docker Compose] --> API
    DOCKER --> DB
    DOCKER --> TESTS
```

**Decisiones:** dependencia hacia adentro (dominio sin SQL/HTTP); una unidad de
trabajo por caso de uso; concurrencia optimista por version; eventos despues
del commit; CQRS sencillo, consultas en la misma base. La API no implementa
las formulas de cargos, solo llama al servicio existente.

Los directorios `src/domain`, `src/application`, `src/infrastructure` y
`src/api` son alias de compatibilidad con la estructura minima del PIA;
la fuente canonica se conserva en `src/novarent/` por continuidad U3.
