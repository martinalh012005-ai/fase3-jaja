-- =====================================================================
-- TDFI103 - Proyecto Semestral 2026 - Fase 2
-- Caso 2: Sistema Integral de Gestión de Centros de Turismo Astronómico
-- 01_schema.sql : creación de la base, tablas, restricciones y triggers
-- Motor: MySQL 8.x
-- =====================================================================

SET NAMES utf8mb4;
DROP DATABASE IF EXISTS turismo_astronomico;
CREATE DATABASE turismo_astronomico
    CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE turismo_astronomico;

-- ---------------------------------------------------------------------
-- TERRITORIO
-- ---------------------------------------------------------------------
CREATE TABLE region (
    id_region                           INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    nombre_oficial                      VARCHAR(80)   NOT NULL,
    superficie_protegida                DECIMAL(10,2) NOT NULL COMMENT 'km2',
    presupuesto_actividades_cientificas DECIMAL(14,2) NOT NULL COMMENT 'CLP',
    CONSTRAINT pk_region PRIMARY KEY (id_region),
    CONSTRAINT uq_region_nombre UNIQUE (nombre_oficial),
    CONSTRAINT ck_region_superficie CHECK (superficie_protegida >= 0),
    CONSTRAINT ck_region_presupuesto CHECK (presupuesto_actividades_cientificas >= 0)
) ENGINE=InnoDB;

CREATE TABLE centro_astronomico (
    id_centro            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    id_region            INT UNSIGNED  NOT NULL,
    nombre               VARCHAR(100)  NOT NULL,
    fecha_inauguracion   DATE          NOT NULL,
    altitud              INT           NOT NULL COMMENT 'metros sobre el nivel del mar',
    latitud              DECIMAL(9,6)  NOT NULL,
    longitud             DECIMAL(9,6)  NOT NULL,
    capacidad_max_diaria INT UNSIGNED  NOT NULL,
    presupuesto_anual    DECIMAL(14,2) NOT NULL COMMENT 'CLP',
    estado_operativo     VARCHAR(15)   NOT NULL DEFAULT 'OPERATIVO',
    nivel_certificacion  VARCHAR(15)   NOT NULL,
    activo               TINYINT(1)    NOT NULL DEFAULT 1 COMMENT 'baja lógica',
    CONSTRAINT pk_centro PRIMARY KEY (id_centro),
    CONSTRAINT uq_centro_nombre UNIQUE (nombre),
    CONSTRAINT fk_centro_region FOREIGN KEY (id_region)
        REFERENCES region (id_region) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_centro_altitud CHECK (altitud >= 0),
    CONSTRAINT ck_centro_lat CHECK (latitud BETWEEN -90 AND 90),
    CONSTRAINT ck_centro_lon CHECK (longitud BETWEEN -180 AND 180),
    CONSTRAINT ck_centro_capacidad CHECK (capacidad_max_diaria > 0),
    CONSTRAINT ck_centro_presupuesto CHECK (presupuesto_anual >= 0),
    CONSTRAINT ck_centro_estado CHECK (estado_operativo IN ('OPERATIVO','MANTENIMIENTO','CERRADO')),
    CONSTRAINT ck_centro_cert CHECK (nivel_certificacion IN ('BASICA','INTERMEDIA','AVANZADA','EXCELENCIA')),
    CONSTRAINT ck_centro_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB;

-- Entidad débil del Centro. Se usa clave sustituta (id_zona) y se conserva
-- la identificación original como UNIQUE (id_centro, numero_interno).
CREATE TABLE zona_observacion (
    id_zona                  INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    id_centro                INT UNSIGNED  NOT NULL,
    numero_interno           SMALLINT UNSIGNED NOT NULL,
    nombre                   VARCHAR(80)   NOT NULL,
    superficie               DECIMAL(8,2)  NOT NULL COMMENT 'm2',
    nivel_oscuridad          TINYINT UNSIGNED NOT NULL COMMENT '1 (más luz) a 10 (cielo más oscuro)',
    capacidad_max            INT UNSIGNED  NOT NULL,
    equipamiento_disponible  VARCHAR(200)  NOT NULL,
    nivel_acceso             VARCHAR(15)   NOT NULL,
    CONSTRAINT pk_zona PRIMARY KEY (id_zona),
    CONSTRAINT uq_zona_centro_numero UNIQUE (id_centro, numero_interno),
    CONSTRAINT fk_zona_centro FOREIGN KEY (id_centro)
        REFERENCES centro_astronomico (id_centro) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_zona_superficie CHECK (superficie > 0),
    CONSTRAINT ck_zona_oscuridad CHECK (nivel_oscuridad BETWEEN 1 AND 10),
    CONSTRAINT ck_zona_capacidad CHECK (capacidad_max > 0),
    CONSTRAINT ck_zona_acceso CHECK (nivel_acceso IN ('PUBLICO','RESTRINGIDO','CIENTIFICO'))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- FENÓMENOS (especialización parcial y disjunta)
-- NOTA: MySQL no permite CHECK sobre columnas que participan en una FK con
-- acciones en cascada; por eso las FK compuestas de subtipos usan RESTRICT.
-- tipo_clasificacion es el discriminador. Cada subtipo repite el
-- discriminador con un CHECK fijo y lo referencia con FK compuesta, de
-- modo que el motor impide que un fenómeno pertenezca a dos subtipos o
-- a uno que no corresponde a su clasificación.
-- ---------------------------------------------------------------------
CREATE TABLE fenomeno_astronomico (
    id_fenomeno                INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre                     VARCHAR(120) NOT NULL,
    descripcion                VARCHAR(400) NOT NULL,
    fecha_primera_observacion  DATE         NULL COMMENT 'dato histórico documentado',
    frecuencia_estimada        VARCHAR(60)  NOT NULL,
    nivel_interes_cientifico   TINYINT UNSIGNED NOT NULL,
    tipo_clasificacion         VARCHAR(20)  NOT NULL DEFAULT 'NO_CLASIFICADO',
    activo                     TINYINT(1)   NOT NULL DEFAULT 1 COMMENT 'baja lógica',
    CONSTRAINT pk_fenomeno PRIMARY KEY (id_fenomeno),
    CONSTRAINT uq_fenomeno_nombre UNIQUE (nombre),
    CONSTRAINT uq_fenomeno_tipo UNIQUE (id_fenomeno, tipo_clasificacion),
    CONSTRAINT ck_fenomeno_interes CHECK (nivel_interes_cientifico BETWEEN 1 AND 5),
    CONSTRAINT ck_fenomeno_tipo CHECK (tipo_clasificacion IN
        ('SOLAR','LUNAR','ESPACIO_PROFUNDO','NO_CLASIFICADO')),
    CONSTRAINT ck_fenomeno_activo CHECK (activo IN (0,1))
) ENGINE=InnoDB;

CREATE TABLE fenomeno_solar (
    id_fenomeno           INT UNSIGNED NOT NULL,
    tipo_clasificacion    VARCHAR(20)  NOT NULL DEFAULT 'SOLAR',
    tipo_evento           VARCHAR(40)  NOT NULL,
    duracion_estimada_min INT UNSIGNED NOT NULL,
    nivel_intensidad      TINYINT UNSIGNED NOT NULL,
    CONSTRAINT pk_solar PRIMARY KEY (id_fenomeno),
    CONSTRAINT fk_solar_fenomeno FOREIGN KEY (id_fenomeno, tipo_clasificacion)
        REFERENCES fenomeno_astronomico (id_fenomeno, tipo_clasificacion),
    CONSTRAINT ck_solar_tipo CHECK (tipo_clasificacion = 'SOLAR'),
    CONSTRAINT ck_solar_duracion CHECK (duracion_estimada_min > 0),
    CONSTRAINT ck_solar_intensidad CHECK (nivel_intensidad BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE fenomeno_lunar (
    id_fenomeno             INT UNSIGNED NOT NULL,
    tipo_clasificacion      VARCHAR(20)  NOT NULL DEFAULT 'LUNAR',
    fase_lunar              VARCHAR(30)  NOT NULL,
    tipo_evento             VARCHAR(40)  NOT NULL,
    visibilidad_porcentaje  DECIMAL(5,2) NOT NULL,
    CONSTRAINT pk_lunar PRIMARY KEY (id_fenomeno),
    CONSTRAINT fk_lunar_fenomeno FOREIGN KEY (id_fenomeno, tipo_clasificacion)
        REFERENCES fenomeno_astronomico (id_fenomeno, tipo_clasificacion),
    CONSTRAINT ck_lunar_tipo CHECK (tipo_clasificacion = 'LUNAR'),
    CONSTRAINT ck_lunar_visibilidad CHECK (visibilidad_porcentaje BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE fenomeno_espacio_profundo (
    id_fenomeno          INT UNSIGNED  NOT NULL,
    tipo_clasificacion   VARCHAR(20)   NOT NULL DEFAULT 'ESPACIO_PROFUNDO',
    tipo_objeto          VARCHAR(40)   NOT NULL,
    distancia_anios_luz  DECIMAL(16,2) NOT NULL,
    magnitud_aparente    DECIMAL(5,2)  NOT NULL,
    CONSTRAINT pk_ep PRIMARY KEY (id_fenomeno),
    CONSTRAINT fk_ep_fenomeno FOREIGN KEY (id_fenomeno, tipo_clasificacion)
        REFERENCES fenomeno_astronomico (id_fenomeno, tipo_clasificacion),
    CONSTRAINT ck_ep_tipo CHECK (tipo_clasificacion = 'ESPACIO_PROFUNDO'),
    CONSTRAINT ck_ep_distancia CHECK (distancia_anios_luz > 0)
) ENGINE=InnoDB;

-- Registro zona-fenómeno (entidad asociativa N:M con identidad propia)
CREATE TABLE observacion (
    id_observacion        INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_zona               INT UNSIGNED NOT NULL,
    id_fenomeno           INT UNSIGNED NOT NULL,
    fecha                 DATE         NOT NULL,
    hora                  TIME         NOT NULL,
    condiciones_climaticas VARCHAR(20) NOT NULL,
    duracion_min          INT UNSIGNED NOT NULL,
    resultado             VARCHAR(20)  NOT NULL,
    CONSTRAINT pk_observacion PRIMARY KEY (id_observacion),
    CONSTRAINT fk_obs_zona FOREIGN KEY (id_zona)
        REFERENCES zona_observacion (id_zona) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_obs_fenomeno FOREIGN KEY (id_fenomeno)
        REFERENCES fenomeno_astronomico (id_fenomeno) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_obs_zona_fen_momento UNIQUE (id_zona, id_fenomeno, fecha, hora),
    CONSTRAINT ck_obs_duracion CHECK (duracion_min > 0),
    CONSTRAINT ck_obs_clima CHECK (condiciones_climaticas IN
        ('DESPEJADO','PARCIALMENTE_NUBLADO','NUBLADO','VIENTO_FUERTE')),
    CONSTRAINT ck_obs_resultado CHECK (resultado IN ('EXITOSA','PARCIAL','FALLIDA'))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- PERSONAS (especialización total y disjunta: VISITANTE / TRABAJADOR)
-- ---------------------------------------------------------------------
CREATE TABLE persona (
    id_persona     INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre_pila    VARCHAR(60)  NOT NULL,
    ap_paterno     VARCHAR(60)  NOT NULL,
    ap_materno     VARCHAR(60)  NULL,
    telefono       VARCHAR(20)  NULL,
    email          VARCHAR(120) NOT NULL,
    tipo_persona   VARCHAR(12)  NOT NULL,
    CONSTRAINT pk_persona PRIMARY KEY (id_persona),
    CONSTRAINT uq_persona_email UNIQUE (email),
    CONSTRAINT uq_persona_tipo UNIQUE (id_persona, tipo_persona),
    CONSTRAINT ck_persona_tipo CHECK (tipo_persona IN ('VISITANTE','TRABAJADOR'))
) ENGINE=InnoDB;

CREATE TABLE visitante (
    id_persona      INT UNSIGNED NOT NULL,
    tipo_persona    VARCHAR(12)  NOT NULL DEFAULT 'VISITANTE',
    fecha_registro  DATE         NOT NULL,
    CONSTRAINT pk_visitante PRIMARY KEY (id_persona),
    CONSTRAINT fk_visitante_persona FOREIGN KEY (id_persona, tipo_persona)
        REFERENCES persona (id_persona, tipo_persona),
    CONSTRAINT ck_visitante_tipo CHECK (tipo_persona = 'VISITANTE')
) ENGINE=InnoDB;

CREATE TABLE trabajador (
    id_persona          INT UNSIGNED NOT NULL,
    tipo_persona        VARCHAR(12)  NOT NULL DEFAULT 'TRABAJADOR',
    id_centro           INT UNSIGNED NOT NULL,
    cargo               VARCHAR(25)  NOT NULL,
    fecha_contratacion  DATE         NOT NULL,
    CONSTRAINT pk_trabajador PRIMARY KEY (id_persona),
    CONSTRAINT fk_trabajador_persona FOREIGN KEY (id_persona, tipo_persona)
        REFERENCES persona (id_persona, tipo_persona),
    CONSTRAINT fk_trabajador_centro FOREIGN KEY (id_centro)
        REFERENCES centro_astronomico (id_centro) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_trabajador_tipo CHECK (tipo_persona = 'TRABAJADOR'),
    CONSTRAINT ck_trabajador_cargo CHECK (cargo IN
        ('ADMINISTRATIVO','GUIA_CIENTIFICO','TECNICO','INVESTIGADOR'))
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- ACTIVIDADES, RESERVAS Y EVALUACIONES
-- ---------------------------------------------------------------------
CREATE TABLE actividad_observacion (
    id_actividad   INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    cod_actividad  VARCHAR(12)   NOT NULL,
    id_zona        INT UNSIGNED  NOT NULL,
    id_guia        INT UNSIGNED  NULL COMMENT 'trabajador con cargo GUIA_CIENTIFICO',
    nombre         VARCHAR(120)  NOT NULL,
    fecha          DATE          NOT NULL,
    horario        TIME          NOT NULL,
    duracion_min   INT UNSIGNED  NOT NULL,
    modalidad      VARCHAR(20)   NOT NULL,
    valor          DECIMAL(10,2) NOT NULL COMMENT 'CLP por visitante',
    capacidad      INT UNSIGNED  NOT NULL,
    estado         VARCHAR(12)   NOT NULL DEFAULT 'PROGRAMADA',
    CONSTRAINT pk_actividad PRIMARY KEY (id_actividad),
    CONSTRAINT uq_actividad_cod UNIQUE (cod_actividad),
    CONSTRAINT fk_actividad_zona FOREIGN KEY (id_zona)
        REFERENCES zona_observacion (id_zona) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_actividad_guia FOREIGN KEY (id_guia)
        REFERENCES trabajador (id_persona) ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT ck_actividad_duracion CHECK (duracion_min > 0),
    CONSTRAINT ck_actividad_valor CHECK (valor >= 0),
    CONSTRAINT ck_actividad_capacidad CHECK (capacidad > 0),
    CONSTRAINT ck_actividad_modalidad CHECK (modalidad IN
        ('NOCTURNA','SOLAR_DIURNA','TALLER','ASTROFOTOGRAFIA','CIENTIFICA_GUIADA')),
    CONSTRAINT ck_actividad_estado CHECK (estado IN ('PROGRAMADA','REALIZADA','CANCELADA'))
) ENGINE=InnoDB;

CREATE TABLE reserva (
    id_reserva          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_visitante        INT UNSIGNED NOT NULL,
    id_actividad        INT UNSIGNED NOT NULL,
    fecha_reserva       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado              VARCHAR(12)  NOT NULL DEFAULT 'CONFIRMADA',
    asistencia_efectiva TINYINT(1)   NOT NULL DEFAULT 0,
    observaciones       VARCHAR(255) NULL,
    CONSTRAINT pk_reserva PRIMARY KEY (id_reserva),
    CONSTRAINT uq_reserva_visitante_actividad UNIQUE (id_visitante, id_actividad),
    CONSTRAINT fk_reserva_visitante FOREIGN KEY (id_visitante)
        REFERENCES visitante (id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_actividad FOREIGN KEY (id_actividad)
        REFERENCES actividad_observacion (id_actividad) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_reserva_estado CHECK (estado IN ('CONFIRMADA','CANCELADA')),
    CONSTRAINT ck_reserva_asistencia CHECK (asistencia_efectiva IN (0,1)),
    CONSTRAINT ck_reserva_coherencia CHECK (NOT (estado = 'CANCELADA' AND asistencia_efectiva = 1))
) ENGINE=InnoDB;

-- Una evaluación por reserva, y solo si el visitante asistió (trigger).
CREATE TABLE evaluacion (
    id_evaluacion  INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_reserva     INT UNSIGNED NOT NULL,
    fecha          DATE         NOT NULL,
    calificacion   TINYINT UNSIGNED NOT NULL,
    comentario     VARCHAR(500) NULL,
    CONSTRAINT pk_evaluacion PRIMARY KEY (id_evaluacion),
    CONSTRAINT uq_evaluacion_reserva UNIQUE (id_reserva),
    CONSTRAINT fk_evaluacion_reserva FOREIGN KEY (id_reserva)
        REFERENCES reserva (id_reserva) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT ck_evaluacion_calificacion CHECK (calificacion BETWEEN 1 AND 5)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- USUARIOS Y ROLES (cuenta -> un rol; rol -> muchas cuentas)
-- ---------------------------------------------------------------------
CREATE TABLE rol (
    id_rol       INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre       VARCHAR(30)  NOT NULL,
    descripcion  VARCHAR(200) NOT NULL,
    permisos     VARCHAR(200) NOT NULL COMMENT 'lista separada por comas',
    activo       TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT pk_rol PRIMARY KEY (id_rol),
    CONSTRAINT uq_rol_nombre UNIQUE (nombre)
) ENGINE=InnoDB;

CREATE TABLE cuenta_usuario (
    id_cuenta        INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_trabajador    INT UNSIGNED NOT NULL,
    id_rol           INT UNSIGNED NOT NULL,
    nombre_usuario   VARCHAR(40)  NOT NULL,
    contrasena_hash  VARCHAR(255) NOT NULL,
    activa           TINYINT(1)   NOT NULL DEFAULT 1,
    CONSTRAINT pk_cuenta PRIMARY KEY (id_cuenta),
    CONSTRAINT uq_cuenta_trabajador UNIQUE (id_trabajador),
    CONSTRAINT uq_cuenta_usuario UNIQUE (nombre_usuario),
    CONSTRAINT fk_cuenta_trabajador FOREIGN KEY (id_trabajador)
        REFERENCES trabajador (id_persona) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_cuenta_rol FOREIGN KEY (id_rol)
        REFERENCES rol (id_rol) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_cuenta_activa CHECK (activa IN (0,1))
) ENGINE=InnoDB;

-- Índices de apoyo a las consultas de los requerimientos
CREATE INDEX ix_actividad_fecha  ON actividad_observacion (fecha, estado);
CREATE INDEX ix_actividad_zona   ON actividad_observacion (id_zona);
CREATE INDEX ix_obs_zona         ON observacion (id_zona);
CREATE INDEX ix_obs_fenomeno     ON observacion (id_fenomeno);
CREATE INDEX ix_reserva_actividad ON reserva (id_actividad);

-- ---------------------------------------------------------------------
-- TRIGGERS: reglas de negocio que un CHECK no puede expresar
-- ---------------------------------------------------------------------
DELIMITER $$

-- RN: la capacidad de una actividad no puede superar la de su zona.
CREATE TRIGGER trg_actividad_capacidad_ins
BEFORE INSERT ON actividad_observacion FOR EACH ROW
BEGIN
    DECLARE v_cap INT UNSIGNED;
    SELECT capacidad_max INTO v_cap FROM zona_observacion WHERE id_zona = NEW.id_zona;
    IF NEW.capacidad > v_cap THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La capacidad de la actividad supera la capacidad máxima de la zona';
    END IF;
END$$

CREATE TRIGGER trg_actividad_capacidad_upd
BEFORE UPDATE ON actividad_observacion FOR EACH ROW
BEGIN
    DECLARE v_cap INT UNSIGNED;
    SELECT capacidad_max INTO v_cap FROM zona_observacion WHERE id_zona = NEW.id_zona;
    IF NEW.capacidad > v_cap THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'La capacidad de la actividad supera la capacidad máxima de la zona';
    END IF;
END$$

-- RN: una reserva confirmada requiere cupo disponible y actividad no cancelada.
CREATE TRIGGER trg_reserva_cupo
BEFORE INSERT ON reserva FOR EACH ROW
BEGIN
    DECLARE v_cap INT UNSIGNED;
    DECLARE v_estado VARCHAR(12);
    DECLARE v_ocupados INT;
    SELECT capacidad, estado INTO v_cap, v_estado
      FROM actividad_observacion WHERE id_actividad = NEW.id_actividad;
    IF v_estado = 'CANCELADA' AND NEW.estado = 'CONFIRMADA' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'No se puede reservar una actividad cancelada';
    END IF;
    IF NEW.estado = 'CONFIRMADA' THEN
        SELECT COUNT(*) INTO v_ocupados FROM reserva
         WHERE id_actividad = NEW.id_actividad AND estado = 'CONFIRMADA';
        IF v_ocupados >= v_cap THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'La actividad no tiene cupos disponibles';
        END IF;
    END IF;
END$$

-- RN: solo puede evaluar quien asistió efectivamente.
CREATE TRIGGER trg_evaluacion_asistencia
BEFORE INSERT ON evaluacion FOR EACH ROW
BEGIN
    DECLARE v_asistio TINYINT(1);
    SELECT asistencia_efectiva INTO v_asistio FROM reserva WHERE id_reserva = NEW.id_reserva;
    IF v_asistio IS NULL OR v_asistio = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Solo se puede evaluar una actividad a la que se asistió';
    END IF;
END$$

DELIMITER ;
