-- =============================================================================
-- PSP-TRUCKS — Esquema de Base de Datos
-- database/schema.sql
-- Fase 2 — Paso 1: Ampliación del modelo de datos
--
-- Cambios respecto a Fase 1:
--   - Tabla trucks rediseñada con el modelo propuesto por el profesor.
--     Se sustituyen los campos (code, truck_id, description, location)
--     por (plate_number, model, capacity_kg, current_location, updated_at).
--   - El ENUM de status añade el estado 'inactive'.
--   - CHECK constraint garantiza capacity_kg > 0 (MySQL >= 8.0.16 lo impone).
--   - Índices en status y plate_number para consultas frecuentes.
--
-- Uso:
--   mysql -u <usuario> -p psp_trucks < database/schema.sql
-- =============================================================================


-- -----------------------------------------------------------------------------
-- roles: tipos de usuario del sistema
-- Sin cambios respecto a Fase 1.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id   INT         NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- users: usuarios con hash bcrypt — NUNCA contraseña en texto plano
-- Sin cambios respecto a Fase 1.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            INT          NOT NULL AUTO_INCREMENT,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,       -- Hash bcrypt ($2b$12$...)
    role_id       INT          NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_users_role
        FOREIGN KEY (role_id) REFERENCES roles(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- audit_logs: registro de eventos de auditoría
-- Sin cambios respecto a Fase 1.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id         INT          NOT NULL AUTO_INCREMENT,
    user_id    INT                   DEFAULT NULL,
    event_type VARCHAR(100) NOT NULL,
    detail     VARCHAR(500)          DEFAULT NULL,
    ip_address VARCHAR(45)           DEFAULT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_logs_user
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- trucks: flota de camiones gestionados por el sistema
--
-- Fase 2 — modelo rediseñado.
-- Se elimina la versión de Fase 1 (DROP) y se crea la nueva estructura.
-- Esto es seguro porque seed.sql recarga los datos iniciales a continuación.
--
-- Campos:
--   plate_number     — matrícula única del camión  (ej. "1234-ABC")
--   model            — marca y modelo              (ej. "Volvo FH16")
--   capacity_kg      — capacidad máxima en kg      (ej. 24000)
--   status           — estado operativo (ENUM de 4 valores)
--   current_location — ubicación actual, nullable  (ej. "Madrid")
--   created_at       — fecha de alta (automática)
--   updated_at       — última modificación (automática)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS trucks;

CREATE TABLE trucks (
    id               INT          NOT NULL AUTO_INCREMENT,
    plate_number     VARCHAR(20)  NOT NULL UNIQUE,
    model            VARCHAR(100) NOT NULL,
    capacity_kg      INT          NOT NULL,
    status           ENUM('available', 'in_transit', 'maintenance', 'inactive')
                                  NOT NULL DEFAULT 'available',
    current_location VARCHAR(100)          DEFAULT NULL,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    -- Integridad: la capacidad debe ser un valor positivo.
    -- MySQL >= 8.0.16 impone esta restricción; versiones anteriores la ignoran.
    CONSTRAINT chk_trucks_capacity CHECK (capacity_kg > 0),

    -- Índices para las consultas más frecuentes de la aplicación.
    INDEX idx_trucks_plate_number (plate_number),
    INDEX idx_trucks_status       (status)

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COMMENT='Flota de camiones — Fase 2';
