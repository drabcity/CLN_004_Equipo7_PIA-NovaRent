"""Implementaciones SQL de Repository y lectores CQRS.

El mapeo reconstruye agregados con sus datos persistidos sin cambiar los modulos
entregados por los integrantes de Dominio y Application.
"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from novarent.aplicacion.consultas import (LectorDePanelDeVehiculos, LectorDeResumenDeCargos, LineaDeCargoDto,
                                           PanelVehiculoDto, ResumenDeCargosDto)
from novarent.dominio import (CatalogoDeCategorias, Categoria, ContratoDeRenta, ContratoDeRentaRepository,
                              DisponibilidadDeVehiculos, Dinero, EntidadNoEncontrada, EstatusDeVehiculo,
                              Id, Reservacion, ReservacionRepository, Vehiculo, VehiculoRepository)
from novarent.dominio.cargo_extra import CargoExtra, TipoDeCargo
from novarent.dominio.reservacion import EstatusDeReservacion
from novarent.dominio.valores import (DocumentacionConductor, InspeccionDeVehiculo, Kilometraje,
                                       NivelDeCombustible, PeriodoDeRenta, VoucherAbierto)
from .base_datos import CategoriaFila, CargoFila, ContratoFila, ReservacionFila, VehiculoFila


class ConflictoDeConcurrencia(Exception):
    """Un segundo agente modifico el mismo agregado. Se revierte la operacion."""


def categoria_desde(fila: CategoriaFila) -> Categoria:
    return Categoria(fila.nombre, fila.nivel, Dinero(fila.tarifa_centavos))


def vehiculo_desde(fila: VehiculoFila) -> Vehiculo:
    vehiculo = Vehiculo(fila.id, fila.placa, categoria_desde(fila.categoria), fila.capacidad_tanque_litros,
                        EstatusDeVehiculo(fila.estatus), fila.desde_minuto)
    vehiculo._persistencia_version = fila.version
    return vehiculo


def reservacion_desde(fila: ReservacionFila) -> Reservacion:
    r = Reservacion(fila.id, categoria_desde(fila.categoria), Dinero(fila.pago_inicial_centavos),
                    PeriodoDeRenta(fila.inicio_minuto, fila.fin_pactado_minuto))
    r._tarifa_diaria = Dinero(fila.tarifa_centavos)  # incluye descuento si hubo downgrade
    r._estatus = EstatusDeReservacion(fila.estatus)
    r._retencion = Dinero(fila.retencion_centavos)
    if fila.titular_licencia is not None:
        r._documentacion = DocumentacionConductor(fila.titular_licencia, fila.edad,
                        fila.vigencia_licencia_minuto, fila.vigencia_identificacion_minuto, bool(fila.identidad_verificada))
    r._persistencia_version = fila.version
    return r


def inspeccion_desde(km: int, octavos: int, danos: int, fotos: int, esquema: bool) -> InspeccionDeVehiculo:
    return InspeccionDeVehiculo(Kilometraje(km), NivelDeCombustible(octavos), danos, fotos, esquema)


def contrato_desde(fila: ContratoFila) -> ContratoDeRenta:
    c = ContratoDeRenta(fila.id, fila.reservacion_id, fila.vehiculo_id, fila.capacidad_tanque_litros,
                       Dinero(fila.tarifa_centavos),
                       VoucherAbierto(fila.voucher_ultimos_4, fila.voucher_autorizacion, fila.voucher_titular),
                       inspeccion_desde(fila.salida_km, fila.salida_octavos, fila.salida_danos, fila.salida_fotos, fila.salida_esquema),
                       PeriodoDeRenta(fila.inicio_minuto, fila.fin_pactado_minuto))
    if fila.devuelto:
        c._devolucion = inspeccion_desde(fila.devolucion_km, fila.devolucion_octavos,
                                        fila.devolucion_danos, fila.devolucion_fotos, fila.devolucion_esquema)
        c._hora_devolucion = fila.hora_devolucion_minuto
        c._devuelto = True
    c._cargos = [CargoExtra(TipoDeCargo(x.tipo), Dinero(x.monto_centavos), x.descripcion, x.cancelado) for x in fila.cargos]
    c._persistencia_version = fila.version
    return c


def _guardar_versionada(sesion: Session, modelo, id: str, version: int | None, campos: dict) -> int:
    if version is None:
        sesion.add(modelo(id=id, version=1, **campos))
        sesion.flush()  # detecta colisiones de claves dentro de la transaccion
        return 1
    resultado = sesion.execute(update(modelo).where(modelo.id == id, modelo.version == version)
                               .values(**campos, version=version + 1))
    if resultado.rowcount != 1:
        raise ConflictoDeConcurrencia(f"Conflicto al guardar {modelo.__tablename__} {id}")
    return version + 1


class ReservacionRepositorioSql(ReservacionRepository):
    def __init__(self, sesion: Session, eventos: list):
        self.sesion, self.eventos = sesion, eventos

    def obtener(self, reservacion_id: Id) -> Reservacion:
        fila = self.sesion.get(ReservacionFila, reservacion_id)
        if fila is None:
            raise EntidadNoEncontrada(f"Reservacion {reservacion_id} no existe")
        return reservacion_desde(fila)

    def guardar(self, r: Reservacion) -> None:
        d = r._documentacion
        campos = dict(categoria_nombre=r.categoria.nombre, tarifa_centavos=r.tarifa_diaria.centavos,
                      pago_inicial_centavos=r.pago_inicial.centavos, inicio_minuto=r.periodo_pactado.inicio,
                      fin_pactado_minuto=r.periodo_pactado.fin_pactado, estatus=r.estatus.value,
                      retencion_centavos=r.retencion.centavos, titular_licencia=d.titular_licencia if d else None,
                      edad=d.edad if d else None, vigencia_licencia_minuto=d.vigencia_licencia if d else None,
                      vigencia_identificacion_minuto=d.vigencia_identificacion if d else None,
                      identidad_verificada=d.identidad_verificada if d else None)
        r._persistencia_version = _guardar_versionada(self.sesion, ReservacionFila, r.id,
                                           getattr(r, "_persistencia_version", None), campos)
        self.eventos.extend(r.extraer_eventos())


class VehiculoRepositorioSql(VehiculoRepository):
    def __init__(self, sesion: Session, eventos: list):
        self.sesion, self.eventos = sesion, eventos

    def obtener(self, vehiculo_id: Id) -> Vehiculo:
        fila = self.sesion.get(VehiculoFila, vehiculo_id)
        if fila is None:
            raise EntidadNoEncontrada(f"Vehiculo {vehiculo_id} no existe")
        return vehiculo_desde(fila)

    def guardar(self, v: Vehiculo) -> None:
        campos = dict(placa=v.placa, categoria_nombre=v.categoria.nombre,
                      capacidad_tanque_litros=v.capacidad_tanque_litros,
                      estatus=v.estatus.value, desde_minuto=v.en_estatus_desde)
        v._persistencia_version = _guardar_versionada(self.sesion, VehiculoFila, v.id,
                                          getattr(v, "_persistencia_version", None), campos)
        self.eventos.extend(v.extraer_eventos())


class ContratoRepositorioSql(ContratoDeRentaRepository):
    def __init__(self, sesion: Session, eventos: list):
        self.sesion, self.eventos = sesion, eventos

    def obtener(self, contrato_id: Id) -> ContratoDeRenta:
        fila = self.sesion.get(ContratoFila, contrato_id)
        if fila is None:
            raise EntidadNoEncontrada(f"Contrato {contrato_id} no existe")
        return contrato_desde(fila)

    def obtener_ultimo_de_vehiculo(self, vehiculo_id: Id) -> ContratoDeRenta:
        fila = self.sesion.scalar(select(ContratoFila).where(ContratoFila.vehiculo_id == vehiculo_id)
                                 .order_by(ContratoFila.inicio_minuto.desc(), ContratoFila.id.desc()).limit(1))
        if fila is None:
            raise EntidadNoEncontrada(f"El vehiculo {vehiculo_id} no tiene contratos")
        return contrato_desde(fila)

    def agregar(self, contrato: ContratoDeRenta) -> None:
        self._guardar(contrato)

    def guardar(self, contrato: ContratoDeRenta) -> None:
        self._guardar(contrato)

    def _guardar(self, c: ContratoDeRenta) -> None:
        salida, dev = c._salida, c._devolucion
        campos = dict(reservacion_id=c.reservacion_id, vehiculo_id=c.vehiculo_id,
                      capacidad_tanque_litros=c._capacidad_tanque_litros, tarifa_centavos=c._tarifa_diaria.centavos,
                      voucher_ultimos_4=c.voucher.ultimos_4, voucher_autorizacion=c.voucher.codigo_autorizacion,
                      voucher_titular=c.voucher.titular, inicio_minuto=c.periodo.inicio,
                      fin_pactado_minuto=c.periodo.fin_pactado, salida_km=salida.kilometraje.valor,
                      salida_octavos=salida.combustible.octavos, salida_danos=salida.marcas_de_dano,
                      salida_fotos=salida.fotografias, salida_esquema=salida.esquema_completado,
                      devolucion_km=dev.kilometraje.valor if c.devuelto else None,
                      devolucion_octavos=dev.combustible.octavos if c.devuelto else None,
                      devolucion_danos=dev.marcas_de_dano if c.devuelto else None,
                      devolucion_fotos=dev.fotografias if c.devuelto else None,
                      devolucion_esquema=dev.esquema_completado if c.devuelto else None,
                      hora_devolucion_minuto=c._hora_devolucion if c.devuelto else None,
                      devuelto=c.devuelto)
        version = getattr(c, "_persistencia_version", None)
        c._persistencia_version = _guardar_versionada(self.sesion, ContratoFila, c.id, version, campos)
        # Los cargos son parte del Aggregate y se sincronizan dentro de la misma transaccion.
        fila = self.sesion.get(ContratoFila, c.id)
        fila.cargos.clear()
        for i, cargo in enumerate(c.cargos):
            fila.cargos.append(CargoFila(orden=i, tipo=cargo.tipo.value, monto_centavos=cargo.monto.centavos,
                                        descripcion=cargo.descripcion, cancelado=cargo.cancelado))
        self.sesion.flush()
        self.eventos.extend(c.extraer_eventos())


class DisponibilidadSql(DisponibilidadDeVehiculos):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones

    def buscar_disponible_de_categoria(self, categoria: Categoria) -> Vehiculo | None:
        with self._fabrica() as sesion:
            fila = sesion.scalar(select(VehiculoFila).where(VehiculoFila.categoria_nombre == categoria.nombre,
                  VehiculoFila.estatus == EstatusDeVehiculo.DISPONIBLE.value).order_by(VehiculoFila.id).limit(1))
            return vehiculo_desde(fila) if fila else None

    def hay_disponibilidad_en(self, categoria: Categoria) -> bool:
        return self.buscar_disponible_de_categoria(categoria) is not None


class CatalogoSql(CatalogoDeCategorias):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones

    def superior_inmediata_de(self, categoria: Categoria) -> Categoria | None:
        with self._fabrica() as s:
            fila = s.scalar(select(CategoriaFila).where(CategoriaFila.nivel > categoria.nivel)
                            .order_by(CategoriaFila.nivel).limit(1))
            return categoria_desde(fila) if fila else None

    def inferior_inmediata_de(self, categoria: Categoria) -> Categoria | None:
        with self._fabrica() as s:
            fila = s.scalar(select(CategoriaFila).where(CategoriaFila.nivel < categoria.nivel)
                            .order_by(CategoriaFila.nivel.desc()).limit(1))
            return categoria_desde(fila) if fila else None


class LectorPanelSql(LectorDePanelDeVehiculos):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones

    def leer(self) -> list[PanelVehiculoDto]:
        with self._fabrica() as s:
            filas = s.scalars(select(VehiculoFila).order_by(VehiculoFila.id)).all()
            return [PanelVehiculoDto(v.id, v.placa, v.categoria_nombre, v.estatus, v.desde_minuto) for v in filas]


class LectorResumenCargosSql(LectorDeResumenDeCargos):
    def __init__(self, fabrica_sesiones):
        self._fabrica = fabrica_sesiones

    def leer(self, contrato_id: Id) -> ResumenDeCargosDto:
        with self._fabrica() as s:
            fila = s.get(ContratoFila, contrato_id)
            if fila is None:
                raise EntidadNoEncontrada(f"Contrato {contrato_id} no existe")
            lineas = tuple(LineaDeCargoDto(x.tipo, x.descripcion, str(Dinero(x.monto_centavos)), x.cancelado)
                            for x in fila.cargos)
            total = sum(x.monto_centavos for x in fila.cargos if not x.cancelado)
            return ResumenDeCargosDto(fila.id, lineas, str(Dinero(total)))
