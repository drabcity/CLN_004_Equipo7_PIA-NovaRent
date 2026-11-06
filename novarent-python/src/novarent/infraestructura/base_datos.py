"""Esquema relacional de NovaRent, independiente del dominio (DDD)."""
from __future__ import annotations

import os
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class CategoriaFila(Base):
    __tablename__ = "categorias"
    nombre: Mapped[str] = mapped_column(String(80), primary_key=True)
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    tarifa_centavos: Mapped[int] = mapped_column(Integer, nullable=False)


class VehiculoFila(Base):
    __tablename__ = "vehiculos"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    placa: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    categoria_nombre: Mapped[str] = mapped_column(ForeignKey("categorias.nombre"), nullable=False)
    capacidad_tanque_litros: Mapped[int] = mapped_column(Integer, nullable=False)
    estatus: Mapped[str] = mapped_column(String(60), nullable=False)
    desde_minuto: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    categoria: Mapped[CategoriaFila] = relationship(lazy="joined")
    __table_args__ = (CheckConstraint("capacidad_tanque_litros > 0"),)


class ReservacionFila(Base):
    __tablename__ = "reservaciones"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    categoria_nombre: Mapped[str] = mapped_column(ForeignKey("categorias.nombre"), nullable=False)
    tarifa_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    pago_inicial_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    inicio_minuto: Mapped[int] = mapped_column(Integer, nullable=False)
    fin_pactado_minuto: Mapped[int] = mapped_column(Integer, nullable=False)
    estatus: Mapped[str] = mapped_column(String(70), nullable=False)
    retencion_centavos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    titular_licencia: Mapped[str | None] = mapped_column(String(160), nullable=True)
    edad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vigencia_licencia_minuto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vigencia_identificacion_minuto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    identidad_verificada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    categoria: Mapped[CategoriaFila] = relationship(lazy="joined")


class ContratoFila(Base):
    __tablename__ = "contratos"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    reservacion_id: Mapped[str] = mapped_column(ForeignKey("reservaciones.id"), nullable=False)
    vehiculo_id: Mapped[str] = mapped_column(ForeignKey("vehiculos.id"), nullable=False)
    capacidad_tanque_litros: Mapped[int] = mapped_column(Integer, nullable=False)
    tarifa_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    voucher_ultimos_4: Mapped[str] = mapped_column(String(4), nullable=False)
    voucher_autorizacion: Mapped[str] = mapped_column(String(100), nullable=False)
    voucher_titular: Mapped[str] = mapped_column(String(160), nullable=False)
    inicio_minuto: Mapped[int] = mapped_column(Integer, nullable=False)
    fin_pactado_minuto: Mapped[int] = mapped_column(Integer, nullable=False)
    salida_km: Mapped[int] = mapped_column(Integer, nullable=False)
    salida_octavos: Mapped[int] = mapped_column(Integer, nullable=False)
    salida_danos: Mapped[int] = mapped_column(Integer, nullable=False)
    salida_fotos: Mapped[int] = mapped_column(Integer, nullable=False)
    salida_esquema: Mapped[bool] = mapped_column(Boolean, nullable=False)
    devolucion_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devolucion_octavos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devolucion_danos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devolucion_fotos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devolucion_esquema: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hora_devolucion_minuto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    devuelto: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cargos: Mapped[list[CargoFila]] = relationship(back_populates="contrato", cascade="all, delete-orphan", order_by="CargoFila.orden")


class CargoFila(Base):
    __tablename__ = "cargos_extra"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contrato_id: Mapped[str] = mapped_column(ForeignKey("contratos.id", ondelete="CASCADE"), nullable=False, index=True)
    orden: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    monto_centavos: Mapped[int] = mapped_column(Integer, nullable=False)
    cancelado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contrato: Mapped[ContratoFila] = relationship(back_populates="cargos")


class EventoPendienteFila(Base):
    __tablename__ = "eventos_pendientes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    agregado_id: Mapped[str] = mapped_column(String(100), nullable=False)
    datos_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    procesado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


def crear_motor(database_url: str | None = None):
    """SQLite local y PostgreSQL en Docker / despliegue, misma interfaz."""
    url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./novarent.db")
    opciones = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        opciones["connect_args"] = {"check_same_thread": False, "timeout": 20}
    motor = create_engine(url, **opciones)
    if url.startswith("sqlite"):
        @event.listens_for(motor, "connect")
        def activar_llaves_foraneas(conexion, _registro):
            cursor = conexion.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return motor


def crear_fabrica_sesiones(motor):
    return sessionmaker(bind=motor, expire_on_commit=False, autoflush=False)


def inicializar_esquema(motor) -> None:
    Base.metadata.create_all(motor)
