"""Lecturas SQL de soporte para US14/US15; las formulas deben validarse con Persona 1.

Utilizacion propuesta: minutos de contratos en el periodo sobre minutos disponibles
(total flota * duracion del intervalo). Se usa el periodo real si se devolvio y
el instante actual si sigue rentado. No cuenta tiempos de limpieza/mantenimiento.
Ingresos: total de cargos NO cancelados, que no necesariamente equivale a cobros pagados.
"""
from __future__ import annotations

from sqlalchemy import func, select
from .base_datos import VehiculoFila, ContratoFila, CargoFila


def reporte_utilizacion(fabrica, inicio_minuto: int, fin_minuto: int, ahora_minuto: int) -> dict:
    if fin_minuto <= inicio_minuto:
        raise ValueError("fin_minuto debe ser mayor que inicio_minuto")
    with fabrica() as s:
        flota = s.scalar(select(func.count(VehiculoFila.id))) or 0
        contratos = s.scalars(select(ContratoFila).where(ContratoFila.inicio_minuto < fin_minuto)).all()
    # Minutos de utilizacion por vehiculo (unificar intervalos para no contar dos veces).
    tramos_por_vehiculo: dict[str, list[tuple[int, int]]] = {}
    for c in contratos:
        fin_real = c.hora_devolucion_minuto if c.devuelto else ahora_minuto
        desde, hasta = max(c.inicio_minuto, inicio_minuto), min(fin_real, fin_minuto)
        if hasta > desde:
            tramos_por_vehiculo.setdefault(c.vehiculo_id, []).append((desde, hasta))
    minutos_rentados = 0
    for intervalos in tramos_por_vehiculo.values():
        actual_inicio, actual_fin = sorted(intervalos)[0]
        for desde, hasta in sorted(intervalos)[1:]:
            if desde <= actual_fin:
                actual_fin = max(actual_fin, hasta)
            else:
                minutos_rentados += actual_fin - actual_inicio
                actual_inicio, actual_fin = desde, hasta
        minutos_rentados += actual_fin - actual_inicio
    denominador = flota * (fin_minuto - inicio_minuto)
    return {"inicio_minuto": inicio_minuto, "fin_minuto": fin_minuto, "total_vehiculos": flota,
            "minutos_rentados": minutos_rentados,
            "tasa_porcentaje": round(100 * minutos_rentados / denominador, 2) if denominador else 0.0,
            "criterio": "Minutos con contrato / (vehiculos actuales x minutos del periodo); formula provisional"}


def reporte_cargos_adicionales(fabrica, inicio_minuto: int, fin_minuto: int) -> dict:
    if fin_minuto <= inicio_minuto:
        raise ValueError("fin_minuto debe ser mayor que inicio_minuto")
    with fabrica() as s:
        filas = s.execute(select(CargoFila.tipo, func.count(CargoFila.id), func.sum(CargoFila.monto_centavos))
              .join(ContratoFila, CargoFila.contrato_id == ContratoFila.id)
              .where(ContratoFila.devuelto.is_(True),
                     ContratoFila.hora_devolucion_minuto >= inicio_minuto,
                     ContratoFila.hora_devolucion_minuto < fin_minuto,
                     CargoFila.cancelado.is_(False)).group_by(CargoFila.tipo)).all()
    detalles = [{"tipo": tipo, "cantidad": cuenta, "monto_centavos": int(monto)} for tipo, cuenta, monto in filas]
    return {"inicio_minuto": inicio_minuto, "fin_minuto": fin_minuto,
            "monto_cargos_no_cancelados_centavos": sum(f["monto_centavos"] for f in detalles),
            "detalle_por_tipo": detalles, "nota": "Cargos calculados; no comprueba pagos bancarios"}
