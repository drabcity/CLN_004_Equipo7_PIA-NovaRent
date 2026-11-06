"""Value Objects del dominio: se definen por sus valores, no tienen identidad."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .comun import Minutos, VoucherInvalido


@dataclass(frozen=True)
class Dinero:
    """Dinero en centavos de peso mexicano (evita errores de punto flotante)."""

    centavos: int = 0

    @staticmethod
    def pesos(p: int) -> "Dinero":
        return Dinero(p * 100)

    def __add__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.centavos + otro.centavos)

    def __sub__(self, otro: "Dinero") -> "Dinero":
        return Dinero(self.centavos - otro.centavos)

    def __mul__(self, n: int) -> "Dinero":
        return Dinero(self.centavos * n)

    def porcentaje(self, pct: int) -> "Dinero":
        return Dinero(self.centavos * pct // 100)

    def __str__(self) -> str:
        signo = "-" if self.centavos < 0 else ""
        c = abs(self.centavos)
        return f"{signo}${c // 100}.{c % 100:02d}"


TarifaDiaria = Dinero


@dataclass(frozen=True)
class Categoria:
    """Glosario #3. La jerarquia se define por 'nivel' (mayor nivel = categoria superior)."""

    nombre: str
    nivel: int = field(default=0, compare=False)
    tarifa_diaria: TarifaDiaria = field(default_factory=Dinero, compare=False)


@dataclass(frozen=True)
class NivelDeCombustible:
    """Glosario #10: nivel fraccional del tanque, en octavos (8 = lleno)."""

    octavos: int = 8

    def __post_init__(self) -> None:
        if not 0 <= self.octavos <= 8:
            raise ValueError("El nivel de combustible va de 0 a 8 octavos")

    def faltante_respecto(self, entregado: "NivelDeCombustible") -> int:
        return max(0, entregado.octavos - self.octavos)


@dataclass(frozen=True)
class Kilometraje:
    valor: int = 0


@dataclass(frozen=True)
class PeriodoDeRenta:
    """Los dias se cuentan por bloques de 24 h (minimo 1)."""

    inicio: Minutos = 0
    fin_pactado: Minutos = 0

    def dias(self) -> int:
        d = self.fin_pactado - self.inicio
        return 1 if d <= 0 else (d + 1439) // 1440


@dataclass(frozen=True)
class VoucherAbierto:
    """Glosario #19 (US12). Se crea solo con crear() para garantizar sus reglas."""

    ultimos_4: str
    codigo_autorizacion: str
    titular: str

    @staticmethod
    def crear(ultimos_4: str, codigo_autorizacion: str, titular_tarjeta: str, titular_licencia: str) -> "VoucherAbierto":
        if not (len(ultimos_4) == 4 and ultimos_4.isdigit()):
            raise VoucherInvalido("se requieren los ultimos 4 digitos de la tarjeta")
        if not codigo_autorizacion:
            raise VoucherInvalido("falta el codigo de autorizacion bancaria")
        if titular_tarjeta != titular_licencia:
            raise VoucherInvalido("la tarjeta debe estar a nombre del titular de la licencia")
        return VoucherAbierto(ultimos_4, codigo_autorizacion, titular_tarjeta)


@dataclass(frozen=True)
class DocumentacionConductor:
    """Glosario #16 y #20 (US10, BRD). 'identidad_verificada' lo confirma el Agente (supuesto S-7)."""

    titular_licencia: str
    edad: int
    vigencia_licencia: Minutos
    vigencia_identificacion: Minutos
    identidad_verificada: bool = False

    def es_valida(self, ahora: Minutos) -> bool:
        return (
            self.identidad_verificada
            and self.edad >= 18
            and self.vigencia_licencia > ahora
            and self.vigencia_identificacion > ahora
        )


@dataclass(frozen=True)
class InspeccionDeVehiculo:
    """Glosario #8, #9. 'esquema_completado' puede ser True sin marcas si no hay danos (supuesto S-8)."""

    kilometraje: Kilometraje = field(default_factory=Kilometraje)
    combustible: NivelDeCombustible = field(default_factory=NivelDeCombustible)
    marcas_de_dano: int = 0
    fotografias: int = 0
    esquema_completado: bool = False

    def esquema_valido(self) -> bool:
        return self.esquema_completado and self.fotografias >= 1


class EstatusDeVehiculo(Enum):  # Glosario #17
    DISPONIBLE = "Disponible"
    RENTADO = "Rentado"
    EN_REVISION = "En revision"
    LIMPIEZA = "Limpieza"
    MANTENIMIENTO_MAYOR = "Mantenimiento Mayor"


class TipoDeCompensacion(Enum):  # Glosario #4 y #5 (US03)
    UPGRADE = "Upgrade"
    DOWNGRADE = "Downgrade"
    NINGUNA = "Ninguna"


@dataclass(frozen=True)
class OfertaDeCompensacion:
    tipo: TipoDeCompensacion = TipoDeCompensacion.NINGUNA
    categoria_destino: Categoria | None = None
    descuento_porcentaje: int = 0
    tarifa_resultante: Dinero = field(default_factory=Dinero)


@dataclass(frozen=True)
class DecisionDelCliente:
    acepta_upgrade: bool = False
    acepta_downgrade: bool = False
