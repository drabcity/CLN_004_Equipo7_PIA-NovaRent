# Formato CSV compatible con el importador

El ZIP original no incluia archivos CSV para NovaRent. Los archivos en `ejemplo/`
son **datos ficticios para ejecutar la demostracion**, no equivalen a los CSV del profesor.

Archivos, UTF-8 y encabezados:

- `categorias.csv`: `nombre,nivel,tarifa_centavos`
- `vehiculos.csv`: `id,placa,categoria,capacidad_tanque_litros`
- `reservaciones.csv`: `id,categoria,pago_inicial_centavos,duracion_dias,inicio_minuto,fin_pactado_minuto`

`inicio_minuto` y `fin_pactado_minuto` son minutos Unix UTC. Si se dejan vacios,
se toma el minuto actual y se suma `duracion_dias` (por defecto 2). Tarifas y pagos
se expresan en centavos MXN: 50000 representa $500.00.

Comando: `python -m novarent.infraestructura.cargar_csv --directorio data/ejemplo`
Repetir la carga no duplica registros con el mismo ID.

**Pendiente:** adaptar los encabezados si los CSV oficiales son diferentes y
validar datos reales con las reglas del BRD. Nunca subir datos de clientes reales
al repositorio.
