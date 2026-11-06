# NovaRent: arquitectura de logica de negocio (codigo base)

Empresa: **NovaRent** (renta de autos). Curso: Componentes de Logica de Negocio, Actividad Unidad 3.
Alcance: 5 casos de uso del flujo de entrega, devolucion y limpieza de vehiculos
(CU-01 entregar, CU-02 validar documentacion, CU-03 compensar categoria, CU-04 devolucion con cargos, CU-05 limpieza).

Equipo: Angelica Reyna Garcia (2144918), Nohemi Delgado Castillo (2145346), Joselyn Maria Quiroga Martinez (2144717).

> El codigo es **parcial a proposito**: muestra la organizacion y las responsabilidades de la arquitectura, no un sistema completo.

## Como ejecutarlo
Requiere Python 3.10 o superior. No hay dependencias.

```bash
python run_tests.py          # 46 pruebas, una por regla de cada caso de uso
# o, si usan pytest:  pip install pytest && pytest
```

## Estructura

```
docs/        Informe (Word), decisiones, trazabilidad y supuestos
diagrams/    Archivos fuente (.puml, .drawio, .dot) y exportaciones (.png)
src/novarent/
  dominio/          Aggregates, Value Objects, Domain Services, politicas de cargo e interfaces de Repository
  aplicacion/       Application Services (uno por caso de uso), puertos, Commands y Queries
  infraestructura/  Adaptadores en memoria (repositorios, Unidad de Trabajo, banco falso) y composition root
tests/       Escenarios por caso de uso (CU-01..CU-05) y pruebas del dominio solo
```

Regla de dependencias: `infraestructura -> aplicacion -> dominio`. El dominio no importa nada de las otras capas.

## Donde mirar primero
| Quiero ver... | Archivo |
|---|---|
| Un Aggregate con sus invariantes | `src/novarent/dominio/vehiculo.py`, `reservacion.py`, `contrato_de_renta.py` |
| Las reglas de cargos (Strategy) | `src/novarent/dominio/politicas_de_cargo.py` |
| Un caso de uso completo con transaccion y compensacion | `src/novarent/aplicacion/servicios.py` (`ServicioDeEntrega`) |
| Repository en terminos del dominio (sin SQL) | `src/novarent/dominio/repositorios.py` |
| Su implementacion en infraestructura | `src/novarent/infraestructura/memoria.py` |
| Commands y Queries (CQRS) | `src/novarent/aplicacion/comandos.py`, `consultas.py` |
| Que regla va a que codigo | `docs/trazabilidad.md` |
| Supuestos sin validar | `docs/supuestos.md` |

## Entregables
- Informe de la actividad: `docs/Actividad_Unidad_3_NovaRent.docx`
- Diagramas fuente: `diagrams/` (mapa de dominio, clases, secuencias)
- Bitacora de uso de IA: pendiente de completar por el equipo (ver el informe)
