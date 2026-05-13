-- =============================================================================
-- PSP-TRUCKS — Datos iniciales
-- database/seed.sql
-- Fase 2 — Paso 1
--
-- Cambios respecto a Fase 1:
--   - Camiones actualizados al nuevo modelo (plate_number, model,
--     capacity_kg, current_location) en lugar de (code, truck_id,
--     description, location).
--   - Se añade un cuarto camión con estado 'inactive' para cubrir
--     los 4 valores del ENUM de status.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Roles del sistema — sin cambios
-- -----------------------------------------------------------------------------
INSERT INTO roles (name) VALUES
    ('user'),
    ('admin')
ON DUPLICATE KEY UPDATE name = VALUES(name);


-- -----------------------------------------------------------------------------
-- Usuarios con hashes bcrypt reales — sin cambios
-- Contraseñas: conductor1 → "password123"  |  admin → "admin123"
-- NUNCA almacenar contraseñas en texto plano.
-- -----------------------------------------------------------------------------
INSERT INTO users (username, password_hash, role_id) VALUES
    (
        'conductor1',
        '$2b$12$IZ8qtJLP6SH2KSTOlvKFwOkN4D7J5.6mUAUQtz21Ms3uTeTSE5JWa',
        (SELECT id FROM roles WHERE name = 'user')
    ),
    (
        'admin',
        '$2b$12$S2HyZLjEfayTmlT2aQ7cJ.MwBQshTJTQH.CDDObOSTJvEwJ5MI3F2',
        (SELECT id FROM roles WHERE name = 'admin')
    )
ON DUPLICATE KEY UPDATE
    password_hash = VALUES(password_hash),
    role_id       = VALUES(role_id);


-- -----------------------------------------------------------------------------
-- Camiones iniciales de la flota — nuevo modelo Fase 2
--
-- Capacidades de referencia (carga útil típica):
--   Volvo FH16    → 24 000 kg
--   Scania R500   → 20 000 kg
--   MAN TGX 26    → 18 000 kg
--   Mercedes 2545 → 22 000 kg (ejemplo de camión inactivo/retirado)
-- -----------------------------------------------------------------------------
INSERT INTO trucks (plate_number, model, capacity_kg, status, current_location) VALUES
    ('1234-ABC', 'Volvo FH16',          24000, 'available',   'León'),
    ('5678-DEF', 'Scania R500',         20000, 'in_transit',  'Madrid'),
    ('9012-GHI', 'MAN TGX 26.440',      18000, 'maintenance', 'Taller Central'),
    ('3456-JKL', 'Mercedes-Benz 2545',  22000, 'inactive',     NULL)
ON DUPLICATE KEY UPDATE
    model            = VALUES(model),
    capacity_kg      = VALUES(capacity_kg),
    status           = VALUES(status),
    current_location = VALUES(current_location);
