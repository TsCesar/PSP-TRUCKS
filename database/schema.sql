-- =============================================================================
-- PSP-TRUCKS — Esquema de Base de Datos
-- database/schema.sql
-- Fase 1 — Paso 3
--
-- Uso:
--   mysql -u <usuario> -p psp_trucks < database/schema.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- roles: tipos de usuario del sistema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id   INT         NOT NULL AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -----------------------------------------------------------------------------
-- users: usuarios con hash bcrypt — NUNCA contraseña en texto plano
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
-- audit_logs: registro de eventos de auditoría (Paso 7)
-- Se crea ahora para no modificar el esquema después.
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
-- Tabla: trucks
-- Almacena los camiones de la flota.
-- Cualquier usuario autenticado puede añadir y eliminar camiones.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trucks (
    id          INT          NOT NULL AUTO_INCREMENT,
    code        VARCHAR(10)  NOT NULL UNIQUE,   -- Código corto: T001, T002...
    truck_id    VARCHAR(20)  NOT NULL UNIQUE,   -- ID completo: TRUCK-001
    description VARCHAR(100) NOT NULL,          -- Descripción del camión
    status      VARCHAR(20)  NOT NULL DEFAULT 'available',  -- available, in_transit, maintenance
    location    VARCHAR(100) NOT NULL DEFAULT 'Sin asignar',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;