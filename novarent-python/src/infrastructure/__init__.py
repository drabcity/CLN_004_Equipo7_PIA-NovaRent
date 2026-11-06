"""Ruta de compatibilidad PIA; implementacion en novarent.infraestructura."""
from novarent.infraestructura.contenedor_sql import construir_con_sql
from novarent.infraestructura.unidad_de_trabajo_sql import UnidadDeTrabajoSql
__all__ = ["construir_con_sql", "UnidadDeTrabajoSql"]
