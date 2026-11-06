"""Importacion idempotente de CSV (categorias, vehiculos, reservaciones).

No estaban adjuntos los CSV del maestro. data/ejemplo contiene datos SOLO para demostracion.
El importador acepta los encabezados documentados en data/README.md.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from sqlalchemy import select
from novarent.dominio import Categoria, Dinero, PeriodoDeRenta, Reservacion, Vehiculo
from .base_datos import CategoriaFila, VehiculoFila, ReservacionFila, crear_fabrica_sesiones, crear_motor, inicializar_esquema
from .contenedor_sql import RelojSistema
from .repositorios_sql import ReservacionRepositorioSql, VehiculoRepositorioSql


def _filas(path: Path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def importar_csv(directorio: str | Path, fabrica_sesiones, ahora: int | None = None) -> dict[str, int]:
    directorio = Path(directorio)
    if not directorio.exists():
        raise FileNotFoundError(f"No existe el directorio {directorio}")
    ahora = RelojSistema().ahora() if ahora is None else ahora
    conteo = {"categorias": 0, "vehiculos": 0, "reservaciones": 0}
    # La misma transaccion para los 3 archivos: no quedan cargas a medias.
    with fabrica_sesiones.begin() as s:
        for fila in _filas(directorio / "categorias.csv"):
            nombre = fila["nombre"].strip()
            if s.get(CategoriaFila, nombre) is None:
                s.add(CategoriaFila(nombre=nombre, nivel=int(fila["nivel"]), tarifa_centavos=int(fila["tarifa_centavos"])))
                conteo["categorias"] += 1
        s.flush()
        cat = {c.nombre: c for c in s.scalars(select(CategoriaFila)).all()}
        for fila in _filas(directorio / "vehiculos.csv"):
            id_ = fila["id"].strip()
            if s.get(VehiculoFila, id_) is None:
                categoria_nombre = fila["categoria"].strip()
                c = cat[categoria_nombre]
                v = Vehiculo(id_, fila["placa"].strip(), Categoria(c.nombre, c.nivel, Dinero(c.tarifa_centavos)),
                             int(fila["capacidad_tanque_litros"]))
                VehiculoRepositorioSql(s, []).guardar(v)
                conteo["vehiculos"] += 1
        for fila in _filas(directorio / "reservaciones.csv"):
            id_ = fila["id"].strip()
            if s.get(ReservacionFila, id_) is None:
                c = cat[fila["categoria"].strip()]
                inicio = int(fila["inicio_minuto"]) if fila.get("inicio_minuto", "").strip() else ahora
                fin = int(fila["fin_pactado_minuto"]) if fila.get("fin_pactado_minuto", "").strip() else \
                       inicio + 1440 * int(fila.get("duracion_dias") or 2)
                r = Reservacion(id_, Categoria(c.nombre, c.nivel, Dinero(c.tarifa_centavos)),
                               Dinero(int(fila["pago_inicial_centavos"])), PeriodoDeRenta(inicio, fin))
                ReservacionRepositorioSql(s, []).guardar(r)
                conteo["reservaciones"] += 1
    return conteo


def main():
    parser = argparse.ArgumentParser(description="Carga CSV en la base NovaRent, sin duplicar IDs existentes")
    parser.add_argument("--directorio", default="data/ejemplo", help="Carpeta con categorias.csv, vehiculos.csv, reservaciones.csv")
    parser.add_argument("--database-url", default=None, help="Omitir para usar DATABASE_URL o SQLite local")
    args = parser.parse_args()
    motor = crear_motor(args.database_url)
    inicializar_esquema(motor)
    print("Importacion:", importar_csv(args.directorio, crear_fabrica_sesiones(motor)))


if __name__ == "__main__":
    main()
