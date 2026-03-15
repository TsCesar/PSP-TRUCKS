-- =============================================================================
-- PSP-TRUCKS — Datos iniciales
-- database/seed.sql
-- =============================================================================

-- Roles del sistema
INSERT INTO roles (name) VALUES
    ('user'),
    ('admin')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Usuarios con hashes bcrypt reales
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

-- Camiones iniciales de la flota
INSERT INTO trucks (code, truck_id, description, status, location) VALUES
    ('T001', 'TRUCK-001', 'Camion Volvo FH16  - Base Leon',      'available',   'Leon'),
    ('T002', 'TRUCK-002', 'Camion Scania R500 - Ruta Madrid',    'in_transit',  'Madrid'),
    ('T003', 'TRUCK-003', 'Camion MAN TGX     - Taller Central', 'maintenance', 'Taller Central')
ON DUPLICATE KEY UPDATE
    description = VALUES(description),
    status      = VALUES(status),
    location    = VALUES(location);