# Diseno del Sistema — PSP-TRUCKS Fase 2

## Decisiones de diseno

### Separacion de modulos

| Modulo | Solo contiene |
|---|---|
| `server.py` | Sockets, TLS, threading, protocolo JSON, enrutado, banner |
| `auth.py` | Verificacion bcrypt, generacion de token |
| `database.py` | Consultas SQL: usuarios, camiones, auditoria, validacion de esquema |
| `tokens.py` | Almacen de tokens en memoria |
| `rbac.py` | Tabla de permisos, verificacion de rol |
| `client.py` | UI consola, menu, acciones, tablas de visualizacion |

### Por que los camiones estan en MySQL

Los datos de la flota deben **persistir** entre reinicios del servidor y ser accesibles por multiples clientes concurrentes. MySQL garantiza consistencia, integridad referencial (CHECK constraints, ENUM, indices) y permite consultas en tiempo real.

### Por que validate_trucks_schema() al arrancar

La tabla `trucks` fue rediseñada en Fase 2. Si el servidor arranca con el esquema antiguo (Fase 1: `code`, `truck_id`, `description`) se producen errores de columna en todas las operaciones CRUD. Verificar el esquema al inicio y detener el servidor con un mensaje claro es preferible a errores crípticos en tiempo de ejecucion.

### Por que todos los usuarios pueden gestionar camiones

El enunciado de Fase 2 pide CRUD de camiones para todos los usuarios autenticados. La gestion de usuarios (create_user, delete_user, list_users) y la auditoria (list_audit_logs, filter_audit_logs_by_user) son privilegio exclusivo de admin.

### Proteccion del usuario 'admin'

El usuario `admin` es el administrador principal. Eliminarlo dejaria el sistema sin acceso privilegiado. La proteccion se implementa en dos capas:
1. **Cliente**: bloquea el intento antes de enviarlo.
2. **Servidor** (`PROTECTED_USERS`): rechaza la operacion independientemente del origen.

### Por que validate_truck_payload() centralizado

`create_truck` y `update_truck` comparten las mismas reglas de validacion (plate_number, model, capacity_kg, status, current_location). Una funcion central evita duplicacion y garantiza consistencia entre ambos handlers.

### Contrasena con asteriscos (solo Windows)

`msvcrt.getwch()` permite leer caracteres sin mostrarlos en la terminal de Windows. Se imprime `*` por cada caracter y se gestiona Backspace. En Linux/macOS se usa `getpass.getpass()` como fallback.

---

## Flujos de operacion

### Login

```
[1] cliente muestra pantalla de login
[2] usuario introduce username y contrasena (contrasena con asteriscos)
[3] cliente envia: {"type":"login", "data":{"username":"...", "password":"..."}}
[4] servidor: authenticate() → MySQL + bcrypt → generate_token()
[5] cliente recibe token, username, role → guarda en session{}
[6] cliente muestra menu adaptado al rol
```

### list_trucks

```
[1] cliente envia: {"type":"list_trucks", "token":"...", "data":{}}
[2] servidor: validate_token() → check_permission() → get_all_trucks() → MySQL
[3] servidor registra TRUCK_LISTED en audit_logs
[4] cliente recibe lista → print_truck_list()
```

### create_truck

```
[1] cliente pide: matricula, modelo, capacidad, estado, ubicacion
[2] cliente valida localmente (campos obligatorios, estado valido)
[3] cliente envia: {"type":"create_truck", "token":"...", "data":{...}}
[4] servidor: validate_truck_payload() → create_truck() → MySQL INSERT
[5] servidor registra TRUCK_CREATED en audit_logs
[6] cliente muestra resultado
```

### update_truck

```
[1] cliente muestra lista de camiones
[2] usuario introduce matricula
[3] cliente consulta truck_detail para mostrar valores actuales
[4] usuario introduce nuevos valores (Enter conserva el actual)
[5] cliente envia: {"type":"update_truck", "token":"...", "data":{...}}
[6] servidor: validate_truck_payload() → update_truck() → MySQL UPDATE
[7] servidor registra TRUCK_UPDATED en audit_logs
[8] cliente muestra resultado
```

### delete_truck

```
[1] cliente muestra lista de camiones
[2] usuario introduce matricula
[3] cliente pide confirmacion (s/n)
[4] cliente envia: {"type":"delete_truck", "token":"...", "data":{"plate_number":"..."}}
[5] servidor: delete_truck() → MySQL DELETE
[6] servidor registra TRUCK_DELETED en audit_logs
[7] cliente muestra resultado
```

### Auditoria admin

```
[1] admin selecciona "Ver auditoria"
[2] submenu: [1] Ultimos registros / [2] Filtrar por usuario
[3] admin introduce limite de registros (default 50)
[4] cliente envia: {"type":"list_audit_logs", "token":"...", "data":{"limit":50}}
[5] servidor: get_audit_logs(limit) → MySQL SELECT con LEFT JOIN users
[6] cliente recibe logs → print_audit_logs()
```

### ACCESS_DENIED

```
[1] usuario (rol user) intenta enviar "list_audit_logs"
[2] servidor: validate_token() OK → check_permission("user","list_audit_logs") → False
[3] servidor: log_event("ACCESS_DENIED", ...)
[4] servidor responde: {"status":"error", "message":"Permiso denegado..."}
[5] cliente muestra error
```

---

## Modelo de datos detallado

### trucks — Fase 2

```sql
CREATE TABLE trucks (
    id               INT          NOT NULL AUTO_INCREMENT,
    plate_number     VARCHAR(20)  NOT NULL UNIQUE,
    model            VARCHAR(100) NOT NULL,
    capacity_kg      INT          NOT NULL,
    status           ENUM('available','in_transit','maintenance','inactive')
                                  NOT NULL DEFAULT 'available',
    current_location VARCHAR(100)          DEFAULT NULL,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT chk_trucks_capacity CHECK (capacity_kg > 0),
    INDEX idx_trucks_plate_number (plate_number),
    INDEX idx_trucks_status       (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Valores validos para status

| Valor | Significado |
|---|---|
| `available` | Disponible en base |
| `in_transit` | En ruta activa |
| `maintenance` | En taller o mantenimiento |
| `inactive` | Retirado o inactivo |

---

## Menus por rol

### Sin sesion

```
[1] Iniciar sesion
[0] Salir
```

### Rol user

```
[1] Ping
[2] Lista de camiones
[3] Detalle de camion
[4] Crear camion
[5] Modificar camion
[6] Eliminar camion
[7] Ayuda / comandos
[8] Cerrar sesion
[0] Salir
```

### Rol admin

```
[1]  Ping
[2]  Lista de camiones
[3]  Detalle de camion
[4]  Crear camion
[5]  Modificar camion
[6]  Eliminar camion
[7]  Lista de usuarios
[8]  Crear usuario
[9]  Eliminar usuario
[10] Ver auditoria
[11] Ayuda / comandos
[12] Cerrar sesion
[0]  Salir
```
