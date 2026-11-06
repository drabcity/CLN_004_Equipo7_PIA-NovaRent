"""Application Services: uno por caso de uso. Coordinan, no concentran reglas de negocio.

Cada metodo publico abre UNA transaccion (ADR-03). Las reglas viven en los Aggregates y Domain Services.
"""
from __future__ import annotations

from typing import Callable

from novarent.dominio import (CalculadoraDeCargosExtra, CompensacionDeCategoria, DecisionDelCliente, DocumentacionConductor,
                              DocumentacionInvalida, ContratoDeRenta, Id, InspeccionDeVehiculo, OfertaDeCompensacion,
                              TipoDeCompensacion, VehiculoNoDisponible, VoucherAbierto, DisponibilidadDeVehiculos, Dinero)

from .comandos import EntregarVehiculo, MarcarVehiculoTerminado, RegistrarDevolucion
from .puertos import (GeneradorDeIds, PasarelaDeAutorizacionBancaria, ProveedorDePrecioDeCombustible, Reloj,
                      UnidadDeTrabajo)

FabricaDeUnidadDeTrabajo = Callable[[], UnidadDeTrabajo]


class ServicioDeValidacionDeDocumentacion:
    """CU-02 y paso 1 de CU-01 (US10)."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow, self._reloj = uow, reloj

    def validar_documentacion_del_conductor(self, reservacion_id: Id, documentacion: DocumentacionConductor) -> bool:
        """True si puede continuar la entrega; False si la documentacion es invalida (reservacion cancelada)."""
        with self._uow() as uow:
            reservacion = uow.reservaciones.obtener(reservacion_id)
            try:
                reservacion.validar_documentacion(documentacion, self._reloj.ahora())
                valida = True
            except DocumentacionInvalida:
                reservacion.cancelar_por_documentacion_invalida()  # retiene 10% del pago inicial
                valida = False
            uow.reservaciones.guardar(reservacion)
            uow.commit()
            return valida


class ServicioDeEntrega:
    """CU-01 (US05, US12, N2). Cambia tres Aggregates en una sola transaccion."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo, disponibilidad: DisponibilidadDeVehiculos,
                 banco: PasarelaDeAutorizacionBancaria, reloj: Reloj, ids: GeneradorDeIds) -> None:
        self._uow, self._disponibilidad, self._banco, self._reloj, self._ids = uow, disponibilidad, banco, reloj, ids

    def entregar_vehiculo(self, cmd: EntregarVehiculo) -> Id:
        # 1) El banco se consulta ANTES de abrir la transaccion (no se retiene una transaccion esperando a un tercero).
        codigo = self._banco.autorizar_deposito(cmd.ultimos_4_tarjeta, cmd.titular_tarjeta)
        try:
            return self._entregar(cmd, codigo)
        except Exception:
            # 2) Compensacion: si algo falla despues de autorizar, se libera el deposito.
            self._banco.liberar_autorizacion(codigo)
            raise

    def _entregar(self, cmd: EntregarVehiculo, codigo: str) -> Id:
        with self._uow() as uow:
            ahora = self._reloj.ahora()
            reservacion = uow.reservaciones.obtener(cmd.reservacion_id)
            vehiculo = self._disponibilidad.buscar_disponible_de_categoria(reservacion.categoria)
            if vehiculo is None:
                raise VehiculoNoDisponible()
            voucher = VoucherAbierto.crear(cmd.ultimos_4_tarjeta, codigo, cmd.titular_tarjeta, reservacion.titular_licencia)
            vehiculo.entregar(ahora)  # N2: solo si esta Disponible
            contrato = ContratoDeRenta.crear(self._ids.nuevo("contrato"), reservacion.id, vehiculo.id,
                                             vehiculo.capacidad_tanque_litros, reservacion.tarifa_diaria,
                                             voucher, cmd.inspeccion_salida, reservacion.periodo_pactado)
            reservacion.marcar_entregada(ahora)
            uow.contratos.agregar(contrato)
            uow.vehiculos.guardar(vehiculo)
            uow.reservaciones.guardar(reservacion)
            uow.commit()
            return contrato.id


class ServicioDeCompensacionDeCategoria:
    """CU-03 (US03, N4)."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo, compensacion: CompensacionDeCategoria) -> None:
        self._uow, self._compensacion = uow, compensacion

    def resolver_categoria_no_disponible(self, reservacion_id: Id, decision: DecisionDelCliente) -> OfertaDeCompensacion:
        with self._uow() as uow:
            reservacion = uow.reservaciones.obtener(reservacion_id)
            oferta = self._compensacion.resolver(reservacion.categoria, decision)
            if oferta.tipo is TipoDeCompensacion.NINGUNA:
                reservacion.cancelar_por_categoria_no_disponible()
            else:
                reservacion.aplicar_compensacion(oferta)
            uow.reservaciones.guardar(reservacion)
            uow.commit()
            return oferta


class ServicioDeDevolucion:
    """CU-04 (US04, US06, US07, N3). El cobro bancario ocurre despues, por el evento CargosExtraCalculados."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo, combustible: ProveedorDePrecioDeCombustible,
                 calculadora: CalculadoraDeCargosExtra, reloj: Reloj) -> None:
        self._uow, self._combustible, self._calculadora, self._reloj = uow, combustible, calculadora, reloj

    def registrar_devolucion(self, cmd: RegistrarDevolucion) -> Id:
        precio = self._combustible.precio_por_litro_actual()
        with self._uow() as uow:
            contrato = uow.contratos.obtener(cmd.contrato_id)
            vehiculo = uow.vehiculos.obtener(contrato.vehiculo_id)
            contrato.registrar_devolucion(cmd.inspeccion_devolucion, cmd.hora_devolucion, precio, self._calculadora)
            vehiculo.recibir_en_revision(self._reloj.ahora())
            uow.contratos.guardar(contrato)
            uow.vehiculos.guardar(vehiculo)
            uow.commit()
            return contrato.id


class ServicioDeLimpieza:
    """CU-05 (US11, US13)."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo, reloj: Reloj) -> None:
        self._uow, self._reloj = uow, reloj

    def iniciar_limpieza(self, vehiculo_id: Id) -> None:
        with self._uow() as uow:
            vehiculo = uow.vehiculos.obtener(vehiculo_id)
            vehiculo.iniciar_limpieza(self._reloj.ahora())
            uow.vehiculos.guardar(vehiculo)
            uow.commit()

    def marcar_terminado(self, cmd: MarcarVehiculoTerminado) -> Id:
        with self._uow() as uow:
            vehiculo = uow.vehiculos.obtener(cmd.vehiculo_id)
            vehiculo.marcar_terminado(self._reloj.ahora())
            uow.vehiculos.guardar(vehiculo)
            uow.commit()
            return vehiculo.id

    def reportar_mantenimiento_mayor(self, vehiculo_id: Id, motivo: str, monto: Dinero) -> None:
        """El cargo retroactivo al ultimo contrato lo agrega ManejadorDeMantenimientoMayor, por evento."""
        with self._uow() as uow:
            vehiculo = uow.vehiculos.obtener(vehiculo_id)
            vehiculo.reportar_mantenimiento_mayor(self._reloj.ahora(), motivo, monto)
            uow.vehiculos.guardar(vehiculo)
            uow.commit()


class ManejadorDeMantenimientoMayor:
    """Reacciona a MantenimientoMayorRegistrado: agrega el cargo retroactivo en OTRA transaccion
    (consistencia eventual entre Aggregates, ADR-02 y ADR-03)."""

    def __init__(self, uow: FabricaDeUnidadDeTrabajo) -> None:
        self._uow = uow

    def __call__(self, evento) -> None:
        with self._uow() as uow:
            contrato = uow.contratos.obtener_ultimo_de_vehiculo(evento.agregado_id)
            contrato.agregar_cargo_retroactivo(Dinero(evento.datos["monto_centavos"]), evento.datos.get("motivo", ""))
            uow.contratos.guardar(contrato)
            uow.commit()
