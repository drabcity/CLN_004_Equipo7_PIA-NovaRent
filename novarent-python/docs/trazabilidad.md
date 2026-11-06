# Trazabilidad: caso de uso -> servicio -> Aggregates -> prueba

| CU | Application Service / Query | Aggregates y Domain Services | Pruebas |
|---|---|---|---|
| CU-01 Entregar vehiculo | `ServicioDeEntrega.entregar_vehiculo` | Vehiculo, ContratoDeRenta (nuevo), Reservacion | `tests/test_cu01_cu02_entrega.py::TestCU01EntregarVehiculo` |
| CU-02 Validar documentacion | `ServicioDeValidacionDeDocumentacion.validar_documentacion_del_conductor` | Reservacion | `tests/test_cu01_cu02_entrega.py::TestCU02ValidarDocumentacion` |
| CU-03 Compensar categoria | `ServicioDeCompensacionDeCategoria.resolver_categoria_no_disponible`; Query `ConsultarOfertaDeCompensacionHandler` | Reservacion + `CompensacionDeCategoria` | `tests/test_cu03_compensacion.py` |
| CU-04 Registrar devolucion | `ServicioDeDevolucion.registrar_devolucion`; Query `ConsultarResumenDeCargosHandler` | ContratoDeRenta + `CalculadoraDeCargosExtra` (3 politicas), Vehiculo | `tests/test_cu04_devolucion.py` |
| CU-05 Limpieza | `ServicioDeLimpieza`; `ManejadorDeMantenimientoMayor`; Query `ConsultarPanelDeVehiculosHandler` | Vehiculo, ContratoDeRenta (cargo retroactivo) | `tests/test_cu05_limpieza.py` |

## Reglas de negocio -> donde viven

| Regla | Codigo |
|---|---|
| Solo un vehiculo Disponible se entrega (N2) | `Vehiculo.entregar` |
| Sin esquema de danos y al menos una foto no se firma (US05) | `ContratoDeRenta.crear` |
| Tarjeta a nombre del titular de la licencia (US12) | `VoucherAbierto.crear` |
| Documentacion invalida: cancela y retiene 10% (US10) | `Reservacion.cancelar_por_documentacion_invalida` |
| Upgrade sin costo, downgrade con 20% de descuento (US03, N4) | `CompensacionDeCategoria` |
| Retraso: 120 min de gracia, 20% por hora, mas de 4 h = dia completo (US04) | `CargoPorRetraso` |
| Combustible = litros x precio + $100 (US06) | `CargoPorCombustibleFaltante` |
| 250 km/dia incluidos, $5 por km extra (US07) | `CargoPorKilometrajeExcedente` |
| Solo "Terminado" deja el vehiculo Disponible (US11) | `Vehiculo.marcar_terminado` |
| Cargo retroactivo por Mantenimiento Mayor (US13) | `ManejadorDeMantenimientoMayor` |
| Solo Administracion cancela cargos (US08) | Fuera de los 5 casos de uso: `CargoExtra.cancelado` existe, pero no hay servicio |

## Extension PIA - Integrante 3 (capa fisica / API)

| Requisito | Implementacion | Evidencia automatizada |
|---|---|---|
| Persistencia de los 3 Aggregates | `infraestructura/base_datos.py`, `repositorios_sql.py` | `test_importacion_idempotente_y_persistencia` |
| Unit of Work y rollback | `infraestructura/unidad_de_trabajo_sql.py` | `test_rollback_y_conflicto_version` |
| Concurrencia de vehiculos | `VehiculoFila.version` + actualizacion condicional | `test_rollback_y_conflicto_version` |
| CU-01 Entregar | POST `/api/reservaciones/{id}/entrega` | `test_cu01_cu04_cu05_y_reportes` |
| CU-02 Documentacion | POST `/api/reservaciones/{id}/documentacion` | `test_documentacion_invalida_cancela_con_retencion` |
| CU-03 Compensacion | GET `/oferta`, POST `/compensacion` | `test_upgrade_en_categoria_no_disponible` |
| CU-04 Devolucion/cargos | POST `/api/contratos/{id}/devolucion`, GET `/cargos` | `test_cu01_cu04_cu05_y_reportes` |
| CU-05 Limpieza/Mantenimiento | POST `/api/vehiculos/{id}/iniciar-limpieza`, `/terminar`, `/mantenimiento-mayor` | `test_mantenimiento_retroactivo_post_commit` |
| US14 Tasa de utilizacion (formula pendiente de validar) | GET `/api/reportes/utilizacion` | `test_cu01_cu04_cu05_y_reportes` |
| US15 Cargos adicionales (cargos calculados, no cobros confirmados) | GET `/api/reportes/cargos-adicionales` | `test_cu01_cu04_cu05_y_reportes` |
| OpenAPI/Swagger | `api/main.py`, `docs/api/openapi.json` | `test_health_openapi_y_catalogo` |
| CSV (datos de ejemplo) | `infraestructura/cargar_csv.py` | `test_importacion_idempotente_y_persistencia` |
| DB+App+Tests | `docker-compose.yml`, `Dockerfile` | Revision de Compose en GitHub Actions, ejecución en Docker pendiente |
| Cobertura >= 80% | `pyproject.toml`, `.github/workflows/ci.yml` | `docs/evidencias/pruebas_locales.txt` |

**Trazabilidad por completar en equipo:** la numeracion definitiva de las 15
historias de Usuario y sus criterios Gherkin, asi como formulas US14/US15,
son responsabilidad del Integrante 1 y deben cruzarse con este apendice antes
de la entrega final.
