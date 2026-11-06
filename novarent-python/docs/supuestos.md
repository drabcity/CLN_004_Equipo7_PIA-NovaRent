# Supuestos pendientes de validar

Todo lo que el negocio no define en la Unidad 2 se marca como supuesto. El codigo lo indica con su codigo (S-n).

| # | Supuesto | Donde se ve en el codigo |
|---|---|---|
| S-1 | Monto y momento del pago inicial (base de la retencion del 10%) | `Reservacion.pago_inicial` |
| S-2 | Capacidad del tanque por vehiculo (para convertir octavos en litros) | `Vehiculo.capacidad_tanque_litros` |
| S-3 | No hay regla de calculo del cargo por danos: se captura manualmente | `ContratoDeRenta.registrar_cargo_manual` |
| S-4 | No se define como se sale de Mantenimiento Mayor | `Vehiculo` (estado terminal en el ejemplo) |
| S-5 | Hasta cuando se permite el cargo retroactivo | `ContratoDeRenta.agregar_cargo_retroactivo` |
| S-6 | Quien pasa un vehiculo de En revision a Limpieza | `ServicioDeLimpieza.iniciar_limpieza` |
| S-7 | Que verifica el Agente y que verifica el sistema en la documentacion | `DocumentacionConductor.identidad_verificada` |
| S-8 | Firma sin danos: esquema completado sin marcas y al menos una foto | `InspeccionDeVehiculo.esquema_valido` |
| S-9 | Monto del cargo por Mantenimiento Mayor | `ServicioDeLimpieza.reportar_mantenimiento_mayor(monto)` |
| S-10 | Que operaciones se hacen con el banco y cuando | `PasarelaDeAutorizacionBancaria` |
| S-11 | Retraso: 4 h desde la hora pactada y la fraccion de hora se cobra completa | `CargoPorRetraso` |
