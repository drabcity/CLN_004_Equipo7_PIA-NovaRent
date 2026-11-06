# Decisiones de arquitectura (resumen; el detalle esta en el informe de la actividad)

- **ADR-01 Domain Model** como patron principal (reglas con estados, politicas y excepciones). Transaction Script solo para reportes de lectura.
- **ADR-02 Aggregates separados** (Reservacion, ContratoDeRenta, Vehiculo) que se relacionan solo por id.
- **ADR-03 Una transaccion por caso de uso**; los eventos se publican despues del commit. La autorizacion bancaria se pide antes de abrir la transaccion y se libera como compensacion si el caso de uso falla.

## SOLID en el codigo
- **S**: `ContratoDeRenta` calcula cargos pero no cambia el estatus del `Vehiculo`; eso lo coordina `ServicioDeDevolucion`.
- **O**: nuevo tipo de cargo automatico = nueva `PoliticaDeCargo` (ver `tests/test_dominio.py`).
- **L**: Danos y Mantenimiento Mayor no son politicas (no tienen regla de calculo); asi ninguna politica lanza "no implementado".
- **I**: `VehiculoRepository` y `DisponibilidadDeVehiculos` estan separados; Limpieza no necesita buscar disponibilidad.
- **D**: los servicios dependen de puertos (`aplicacion/puertos.py`); los adaptadores se conectan en `infraestructura/contenedor.py`.

## Diferencias entre el diseno del informe y este codigo (a proposito)
- Los adaptadores son **en memoria** (`infraestructura/memoria.py`); el informe nombra `*Sql` como ejemplo de implementacion real.
- `RegistrarDevolucion` incluye `hora_devolucion` para que la prueba sea determinista; en un sistema real vendria del `Reloj`.
- El panel y el resumen de cargos leen del mismo almacen (CQRS basico, misma base de datos).
