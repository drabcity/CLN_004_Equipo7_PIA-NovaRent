"""Adaptadores EN MEMORIA de los puertos y repositorios.

Sirven para ejecutar los casos de uso y las pruebas sin base de datos. En produccion se sustituyen por
adaptadores SQL (ReservacionRepositorioSql, etc.) sin tocar dominio ni aplicacion (principio D de SOLID).
Los repositorios guardan COPIAS de los Aggregates, como lo haria una base de datos.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from typing import Callable

from novarent.aplicacion.consultas import (LectorDePanelDeVehiculos, LectorDeResumenDeCargos, LineaDeCargoDto,
                                           PanelVehiculoDto, ResumenDeCargosDto)
from novarent.aplicacion.puertos import (GeneradorDeIds, PasarelaDeAutorizacionBancaria, ProveedorDePrecioDeCombustible,
                                         PublicadorDeEventos, Reloj, UnidadDeTrabajo)
from novarent.dominio import (CatalogoDeCategorias, Categoria, ContratoDeRenta, ContratoDeRentaRepository,
                              DisponibilidadDeVehiculos, Dinero, EntidadNoEncontrada, EstatusDeVehiculo, EventoDeDominio,
                              Id, Minutos, Reservacion, ReservacionRepository, Vehiculo, VehiculoRepository)


class Almacen:
    """La 'base de datos' en memoria. Una sola fuente de verdad para escritura y lectura (CQRS basico)."""

    def __init__(self) -> None:
        self.reservaciones: dict[Id, Reservacion] = {}
        self.contratos: dict[Id, ContratoDeRenta] = {}
        self.vehiculos: dict[Id, Vehiculo] = {}
        self.categorias: list[Categoria] = []  # ordenadas por nivel

    def instantanea(self):
        return copy.deepcopy((self.reservaciones, self.contratos, self.vehiculos))

    def restaurar(self, snap) -> None:
        self.reservaciones, self.contratos, self.vehiculos = snap


class _RepoBase:
    def __init__(self, almacen: Almacen, eventos: list[EventoDeDominio]) -> None:
        self._a, self._eventos = almacen, eventos

    def _guardar(self, tabla: dict, agregado) -> None:
        self._eventos.extend(agregado.extraer_eventos())  # los eventos viajan con la transaccion
        tabla[agregado.id] = copy.deepcopy(agregado)

    @staticmethod
    def _leer(tabla: dict, id: Id, nombre: str):
        if id not in tabla:
            raise EntidadNoEncontrada(f"{nombre} {id} no existe")
        return copy.deepcopy(tabla[id])


class ReservacionRepositorioEnMemoria(_RepoBase, ReservacionRepository):
    def obtener(self, reservacion_id: Id) -> Reservacion:
        return self._leer(self._a.reservaciones, reservacion_id, "Reservacion")

    def guardar(self, reservacion: Reservacion) -> None:
        self._guardar(self._a.reservaciones, reservacion)


class ContratoRepositorioEnMemoria(_RepoBase, ContratoDeRentaRepository):
    def obtener(self, contrato_id: Id) -> ContratoDeRenta:
        return self._leer(self._a.contratos, contrato_id, "Contrato")

    def agregar(self, contrato: ContratoDeRenta) -> None:
        self._guardar(self._a.contratos, contrato)

    def guardar(self, contrato: ContratoDeRenta) -> None:
        self._guardar(self._a.contratos, contrato)

    def obtener_ultimo_de_vehiculo(self, vehiculo_id: Id) -> ContratoDeRenta:
        del_vehiculo = [c for c in self._a.contratos.values() if c.vehiculo_id == vehiculo_id]
        if not del_vehiculo:
            raise EntidadNoEncontrada(f"El vehiculo {vehiculo_id} no tiene contratos")
        return copy.deepcopy(del_vehiculo[-1])  # los dicts conservan el orden de insercion


class VehiculoRepositorioEnMemoria(_RepoBase, VehiculoRepository):
    def obtener(self, vehiculo_id: Id) -> Vehiculo:
        return self._leer(self._a.vehiculos, vehiculo_id, "Vehiculo")

    def guardar(self, vehiculo: Vehiculo) -> None:
        self._guardar(self._a.vehiculos, vehiculo)


class DisponibilidadEnMemoria(DisponibilidadDeVehiculos):
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def buscar_disponible_de_categoria(self, categoria: Categoria) -> Vehiculo | None:
        for v in self._a.vehiculos.values():
            if v.categoria == categoria and v.estatus is EstatusDeVehiculo.DISPONIBLE:
                return copy.deepcopy(v)
        return None

    def hay_disponibilidad_en(self, categoria: Categoria) -> bool:
        return self.buscar_disponible_de_categoria(categoria) is not None


class CatalogoEnMemoria(CatalogoDeCategorias):
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def _ordenadas(self) -> list[Categoria]:
        return sorted(self._a.categorias, key=lambda c: c.nivel)

    def superior_inmediata_de(self, categoria: Categoria) -> Categoria | None:
        return next((c for c in self._ordenadas() if c.nivel > categoria.nivel), None)

    def inferior_inmediata_de(self, categoria: Categoria) -> Categoria | None:
        return next((c for c in reversed(self._ordenadas()) if c.nivel < categoria.nivel), None)


class UnidadDeTrabajoEnMemoria(UnidadDeTrabajo):
    """Transaccion por instantanea: si no hay commit, se restaura el estado anterior."""

    def __init__(self, almacen: Almacen, publicador: PublicadorDeEventos) -> None:
        self._a, self._publicador = almacen, publicador
        self._eventos: list[EventoDeDominio] = []
        self._snap = None
        self._confirmada = False
        self.reservaciones = ReservacionRepositorioEnMemoria(almacen, self._eventos)
        self.contratos = ContratoRepositorioEnMemoria(almacen, self._eventos)
        self.vehiculos = VehiculoRepositorioEnMemoria(almacen, self._eventos)

    def __enter__(self) -> "UnidadDeTrabajoEnMemoria":
        self._snap, self._confirmada = self._a.instantanea(), False
        self._eventos.clear()
        return self

    def __exit__(self, tipo, valor, traza) -> None:
        if not self._confirmada:
            self.rollback()

    def commit(self) -> None:
        self._confirmada = True
        self._snap = None
        pendientes, eventos = list(self._eventos), None
        self._eventos.clear()
        for evento in pendientes:  # ADR-03: los eventos salen despues del commit
            self._publicador.publicar(evento)

    def rollback(self) -> None:
        if self._snap is not None:
            self._a.restaurar(self._snap)
        self._snap = None
        self._eventos.clear()


# ---------------------------------------------------------------- publicador y fakes de servicios externos
class PublicadorEnMemoria(PublicadorDeEventos):
    def __init__(self) -> None:
        self.publicados: list[EventoDeDominio] = []
        self._suscriptores: dict[str, list[Callable[[EventoDeDominio], None]]] = defaultdict(list)

    def suscribir(self, nombre_evento: str, manejador: Callable[[EventoDeDominio], None]) -> None:
        self._suscriptores[nombre_evento].append(manejador)

    def publicar(self, evento: EventoDeDominio) -> None:
        self.publicados.append(evento)
        for manejador in self._suscriptores[evento.nombre]:
            manejador(evento)

    def nombres(self) -> list[str]:
        return [e.nombre for e in self.publicados]


class PasarelaBancariaFalsa(PasarelaDeAutorizacionBancaria):
    def __init__(self, rechazar: bool = False) -> None:
        self.rechazar = rechazar
        self.autorizaciones: list[str] = []
        self.liberadas: list[str] = []
        self.cobros: list[tuple[str, Dinero]] = []

    def autorizar_deposito(self, ultimos_4: str, titular_tarjeta: str) -> str:
        if self.rechazar:
            raise RuntimeError("El banco rechazo la autorizacion")
        codigo = f"AUT-{len(self.autorizaciones) + 1:04d}"
        self.autorizaciones.append(codigo)
        return codigo

    def liberar_autorizacion(self, codigo_autorizacion: str) -> None:
        self.liberadas.append(codigo_autorizacion)

    def cobrar_cargos(self, codigo_autorizacion: str, monto: Dinero) -> None:
        self.cobros.append((codigo_autorizacion, monto))


class PrecioDeCombustibleFijo(ProveedorDePrecioDeCombustible):
    def __init__(self, precio: Dinero) -> None:
        self._precio = precio

    def precio_por_litro_actual(self) -> Dinero:
        return self._precio


class RelojFijo(Reloj):
    def __init__(self, ahora: Minutos = 0) -> None:
        self._ahora = ahora

    def ahora(self) -> Minutos:
        return self._ahora

    def avanzar(self, minutos: Minutos) -> None:
        self._ahora += minutos


class GeneradorSecuencial(GeneradorDeIds):
    def __init__(self) -> None:
        self._n = 0

    def nuevo(self, prefijo: str) -> Id:
        self._n += 1
        return f"{prefijo}-{self._n:03d}"


# ---------------------------------------------------------------- lectores (lado Query de CQRS)
class LectorPanelEnMemoria(LectorDePanelDeVehiculos):
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def leer(self) -> list[PanelVehiculoDto]:
        return [PanelVehiculoDto(v.id, v.placa, v.categoria.nombre, v.estatus.value, v.en_estatus_desde)
                for v in self._a.vehiculos.values()]


class LectorResumenCargosEnMemoria(LectorDeResumenDeCargos):
    def __init__(self, almacen: Almacen) -> None:
        self._a = almacen

    def leer(self, contrato_id: Id) -> ResumenDeCargosDto:
        c = self._a.contratos.get(contrato_id)
        if c is None:
            raise EntidadNoEncontrada(f"Contrato {contrato_id} no existe")
        lineas = tuple(LineaDeCargoDto(x.tipo.value, x.descripcion, str(x.monto), x.cancelado) for x in c.cargos)
        return ResumenDeCargosDto(c.id, lineas, str(c.total_cargos()))
