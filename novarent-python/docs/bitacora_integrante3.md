# Bitacora de Integrante 3 (trabajo sobre ZIP recibido)

| Secuencia | Actividad | Resultado / evidencia |
|---|---|---|
| 1 | Revisar codigo base U3 | 46 pruebas originales exitosas; sin SQL ni API |
| 2 | Modelar persistencia | SQLAlchemy con categorias, vehiculos, reservaciones, contratos, cargos y outbox |
| 3 | Implementar puertos | Repository SQL, consulta disponibilidad y Unit of Work con rollback |
| 4 | API REST | FastAPI con rutas CU-01..CU-05, Swagger y OpenAPI |
| 5 | Importacion CSV | Script idempotente y archivos de ejemplo; CSV oficiales faltantes |
| 6 | Calidad | Pruebas de integracion, errores HTTP, transacciones, reentrada y concurrencia |
| 7 | Reportes | US14/US15 de solo lectura con formulas provisionales por validar |
| 8 | Automatizacion | Docker Compose DB/App/Tests, Dockerfile, GitHub Actions, .env.example |
| 9 | Revision local | 57 pruebas exitosas y cobertura total 96.36% en el entorno local |

**Sin verificar aun:** pipeline remoto GitHub, arranque Docker/PostgreSQL en el
equipo, despliegue Render, CSV oficiales y formulas definitivas de reportes.

Los cambios del dominio y la capa Application originales no se sustituyeron;
los adaptadores SQL respetan sus contratos para que el resto del equipo pueda
integrar futuras correcciones con menor riesgo.
