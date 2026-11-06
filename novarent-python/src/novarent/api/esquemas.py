"""DTOs HTTP. El dominio no importa FastAPI ni Pydantic."""
from pydantic import BaseModel, Field
from novarent.dominio import InspeccionDeVehiculo, Kilometraje, NivelDeCombustible


class InspeccionEntrada(BaseModel):
    kilometraje: int = Field(ge=0, examples=[12000])
    combustible_octavos: int = Field(ge=0, le=8, examples=[8])
    marcas_de_dano: int = Field(default=0, ge=0)
    fotografias: int = Field(default=1, ge=0)
    esquema_completado: bool = True

    def al_dominio(self) -> InspeccionDeVehiculo:
        return InspeccionDeVehiculo(Kilometraje(self.kilometraje), NivelDeCombustible(self.combustible_octavos),
                                    self.marcas_de_dano, self.fotografias, self.esquema_completado)


class CrearReservacionEntrada(BaseModel):
    categoria: str = Field(min_length=1, examples=["Compacta"])
    pago_inicial_centavos: int = Field(ge=0, examples=[100000])
    duracion_dias: int = Field(default=2, ge=1, le=365)


class DocumentacionEntrada(BaseModel):
    titular_licencia: str = Field(min_length=1, examples=["Ana Perez"])
    edad: int = Field(ge=0, le=120, examples=[30])
    vigencia_licencia_minuto: int = Field(ge=0)
    vigencia_identificacion_minuto: int = Field(ge=0)
    identidad_verificada: bool


class EntregaEntrada(BaseModel):
    ultimos_4_tarjeta: str = Field(pattern=r"^[0-9]{4}$", examples=["4242"])
    titular_tarjeta: str = Field(min_length=1, examples=["Ana Perez"])
    inspeccion_salida: InspeccionEntrada


class DevolucionEntrada(BaseModel):
    hora_devolucion_minuto: int = Field(ge=0)
    inspeccion_devolucion: InspeccionEntrada


class CompensacionEntrada(BaseModel):
    acepta_upgrade: bool = False
    acepta_downgrade: bool = False


class MantenimientoEntrada(BaseModel):
    motivo: str = Field(min_length=1)
    monto_centavos: int = Field(ge=0)
