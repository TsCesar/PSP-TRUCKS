# Diseño del Sistema — PSP-TRUCKS Fase 1

## Decisiones de diseño

### Separación de módulos

| Módulo | Solo contiene |
|---|---|
| `server.py` | Sockets, TLS, threading, protocolo, enrutado |
| `auth.py` | Verificación bcrypt, generación de token |
| `database.py` | Consultas SQL: usuarios, camiones, auditoría |
| `tokens.py` | Almacén de tokens en memoria |
| `rbac.py` | Tabla de permisos, verificación de rol |

### Por qué los camiones están en MySQL y no en memoria

Los datos de la flota deben **persistir** entre reinicios del servidor y ser consultables por múltiples clientes concurrentes. MySQL garantiza consistencia e integridad referencial. Los camiones se consultan siempre desde la BD en tiempo real.

### Por qué todos los usuarios pueden gestionar camiones

El enunciado pide "al menos un comando para todos los usuarios autenticados". Se ha optado por que la gestión de la flota (add_truck, delete_truck) sea universal para todos los roles, dejando la gestión de usuarios (create_user, delete_user) como privilegio exclusivo de admin.

### Protección del usuario 'admin'

El usuario `admin` es el administrador principal del sistema. Eliminarlo dejaría el sistema sin acceso privilegiado. La protección se implementa en dos capas:

1. **Cliente**: bloquea el intento antes de enviar el comando.
2. **Servidor** (`database.py → PROTECTED_USERS`): rechaza la operación independientemente del origen.

### Búsqueda de camiones por código o ID

Los camiones tienen dos identificadores:
- **Código corto** (`T001`, `T002`...): para introducción rápida en el menú.
- **ID completo** (`TRUCK-001`): para compatibilidad con sistemas externos.

`get_truck_by_query()` acepta ambos formatos con una sola consulta SQL:

```sql
WHERE code = %s OR truck_id = %s
```

---

## Flujos de operación

### Añadir camión

```
[1] cliente muestra lista actual de camiones desde MySQL
[2] cliente pide: code, truck_id, description, status, location
[3] cliente envía: {type:"add_truck", token:"...", data:{...}}
[4] servidor: check_permission() → create_truck() → log_event("TRUCK_CREATED")
[5] cliente muestra resultado
```

### Eliminar camión

```
[1] cliente muestra lista actualizada de camiones
[2] usuario introduce código o ID
[3] cliente pide confirmación (s/n)
[4] cliente envía: {type:"delete_truck", token:"...", data:{query:"T001"}}
[5] servidor: check_permission() → delete_truck() → log_event("TRUCK_DELETED")
[6] cliente muestra lista actualizada
```

### Eliminar usuario (admin)

```
[1] cliente muestra lista de usuarios
[2] admin introduce nombre de usuario
[3] cliente bloquea si intenta eliminar 'admin'
[4] cliente pide confirmación
[5] envía: {type:"delete_user", token:"...", data:{username:"conductor1"}}
[6] servidor: PROTECTED_USERS check → delete_user() → log_event("USER_DELETED")
```

---

## Modelo de datos detallado

### trucks

```sql
CREATE TABLE trucks (
    id          INT          NOT NULL AUTO_INCREMENT,
    code        VARCHAR(10)  NOT NULL UNIQUE,
    truck_id    VARCHAR(20)  NOT NULL UNIQUE,
    description VARCHAR(100) NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'available',
    location    VARCHAR(100) NOT NULL DEFAULT 'Sin asignar',
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
```

### Valores válidos para status

| Valor | Significado |
|---|---|
| `available` | Disponible en base |
| `in_transit` | En ruta activa |
| `maintenance` | En taller / mantenimiento |

---

## Menús por rol

### Rol user

```
[1] Ping
[2] Estado de camión
[3] Añadir camión
[4] Eliminar camión
[5] Ayuda / comandos
[6] Cerrar sesión
[0] Salir
```

### Rol admin

```
[1] Ping
[2] Estado de camión
[3] Añadir camión
[4] Eliminar camión
[5] Crear usuario
[6] Eliminar usuario
[7] Ayuda / comandos
[8] Cerrar sesión
[0] Salir
```