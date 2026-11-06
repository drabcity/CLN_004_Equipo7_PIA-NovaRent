# API REST NovaRent

- Swagger interactivo: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Copia estatica del esquema: `docs/api/openapi.json`

## Rutas principales

| Metodo | Ruta | Funcionalidad |
|---|---|---|
| GET | `/health` | Estado de DB |
| GET | `/api/categorias` | Catalogo |
| GET | `/api/vehiculos` | Panel |
| POST | `/api/reservaciones` | Alta tecnica de demostracion |
| GET | `/api/reservaciones/{id}` | Estado y datos principales |
| POST | `/api/reservaciones/{id}/documentacion` | CU-02 |
| GET | `/api/reservaciones/{id}/oferta` | CU-03 lectura |
| POST | `/api/reservaciones/{id}/compensacion` | CU-03 comando |
| POST | `/api/reservaciones/{id}/entrega` | CU-01 |
| POST | `/api/contratos/{id}/devolucion` | CU-04 |
| GET | `/api/contratos/{id}/cargos` | CU-04 lectura |
| POST | `/api/vehiculos/{id}/iniciar-limpieza` | CU-05 |
| POST | `/api/vehiculos/{id}/terminar` | CU-05 |
| POST | `/api/vehiculos/{id}/mantenimiento-mayor` | CU-05 |
| GET | `/api/reportes/utilizacion?inicio_minuto=...&fin_minuto=...` | US14, formula provisional |
| GET | `/api/reportes/cargos-adicionales?inicio_minuto=...&fin_minuto=...` | US15, cargos no cancelados |

Los instantes/vigencias son minutos Unix UTC (no fechas ISO). Importes numericos
se expresan en CENTAVOS MXN. Se usa documentacion del conductor verificada y
fotografia/esquema valido en entrega.

## Ejemplo de validacion

Primero GET `/api/reservaciones/res-demo-1` y consultar `inicio_minuto` (N).
Despues POST `/api/reservaciones/res-demo-1/documentacion`:

```json
{"titular_licencia":"Ana Perez", "edad":30,
 "vigencia_licencia_minuto": 99999999,
 "vigencia_identificacion_minuto": 99999999,
 "identidad_verificada":true}
```

POST `/api/reservaciones/res-demo-1/entrega`:

```json
{"ultimos_4_tarjeta":"4242", "titular_tarjeta":"Ana Perez",
 "inspeccion_salida":{"kilometraje":1000,"combustible_octavos":8,
 "marcas_de_dano":0,"fotografias":2,"esquema_completado":true}}
```

Guardar `contrato_id` de la respuesta para registrar devolucion. En las
vigencias del ejemplo se usa un minuto UTC lejano en el futuro para demostracion;
no introducir datos financieros ni identificadores reales.

Si se configura `API_KEY`, proporcionar encabezado `X-API-Key` a los endpoints,
o usar `Authorize` en Swagger. Los contratos y registros contienen datos de
demostracion exclusivamente.
