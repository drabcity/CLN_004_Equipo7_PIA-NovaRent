-- Esquema de referencia PostgreSQL generado desde SQLAlchemy.
-- El proyecto crea tablas automaticamente en el arranque para la demo.
-- Para produccion real, usar migraciones versionadas (Alembic).


CREATE TABLE categorias (
	nombre VARCHAR(80) NOT NULL, 
	nivel INTEGER NOT NULL, 
	tarifa_centavos INTEGER NOT NULL, 
	PRIMARY KEY (nombre), 
	UNIQUE (nivel)
)

;


CREATE TABLE eventos_pendientes (
	id SERIAL NOT NULL, 
	nombre VARCHAR(100) NOT NULL, 
	agregado_id VARCHAR(100) NOT NULL, 
	datos_json TEXT NOT NULL, 
	procesado BOOLEAN NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE reservaciones (
	id VARCHAR(100) NOT NULL, 
	categoria_nombre VARCHAR(80) NOT NULL, 
	tarifa_centavos INTEGER NOT NULL, 
	pago_inicial_centavos INTEGER NOT NULL, 
	inicio_minuto INTEGER NOT NULL, 
	fin_pactado_minuto INTEGER NOT NULL, 
	estatus VARCHAR(70) NOT NULL, 
	retencion_centavos INTEGER NOT NULL, 
	titular_licencia VARCHAR(160), 
	edad INTEGER, 
	vigencia_licencia_minuto INTEGER, 
	vigencia_identificacion_minuto INTEGER, 
	identidad_verificada BOOLEAN, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(categoria_nombre) REFERENCES categorias (nombre)
)

;


CREATE TABLE vehiculos (
	id VARCHAR(100) NOT NULL, 
	placa VARCHAR(30) NOT NULL, 
	categoria_nombre VARCHAR(80) NOT NULL, 
	capacidad_tanque_litros INTEGER NOT NULL, 
	estatus VARCHAR(60) NOT NULL, 
	desde_minuto INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CHECK (capacidad_tanque_litros > 0), 
	UNIQUE (placa), 
	FOREIGN KEY(categoria_nombre) REFERENCES categorias (nombre)
)

;


CREATE TABLE contratos (
	id VARCHAR(100) NOT NULL, 
	reservacion_id VARCHAR(100) NOT NULL, 
	vehiculo_id VARCHAR(100) NOT NULL, 
	capacidad_tanque_litros INTEGER NOT NULL, 
	tarifa_centavos INTEGER NOT NULL, 
	voucher_ultimos_4 VARCHAR(4) NOT NULL, 
	voucher_autorizacion VARCHAR(100) NOT NULL, 
	voucher_titular VARCHAR(160) NOT NULL, 
	inicio_minuto INTEGER NOT NULL, 
	fin_pactado_minuto INTEGER NOT NULL, 
	salida_km INTEGER NOT NULL, 
	salida_octavos INTEGER NOT NULL, 
	salida_danos INTEGER NOT NULL, 
	salida_fotos INTEGER NOT NULL, 
	salida_esquema BOOLEAN NOT NULL, 
	devolucion_km INTEGER, 
	devolucion_octavos INTEGER, 
	devolucion_danos INTEGER, 
	devolucion_fotos INTEGER, 
	devolucion_esquema BOOLEAN, 
	hora_devolucion_minuto INTEGER, 
	devuelto BOOLEAN NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reservacion_id) REFERENCES reservaciones (id), 
	FOREIGN KEY(vehiculo_id) REFERENCES vehiculos (id)
)

;


CREATE TABLE cargos_extra (
	id SERIAL NOT NULL, 
	contrato_id VARCHAR(100) NOT NULL, 
	orden INTEGER NOT NULL, 
	tipo VARCHAR(60) NOT NULL, 
	descripcion TEXT NOT NULL, 
	monto_centavos INTEGER NOT NULL, 
	cancelado BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contrato_id) REFERENCES contratos (id) ON DELETE CASCADE
)

;

CREATE INDEX ix_cargos_extra_contrato_id ON cargos_extra (contrato_id);

