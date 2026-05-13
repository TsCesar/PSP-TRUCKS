# Diario PSP — PSP-TRUCKS

**Módulo**: PSP (2º DAM) | **Curso**: 2025-2026 | **Alumno**: Cesar Mendez

---

## Registro de sesiones de trabajo

### [23-ene] Análisis del enunciado y primeros pasos

**Objetivo**: Entender el alcance del proyecto y definir la arquitectura.

**Actividades**:
- Lectura completa del enunciado (Fase 1, 8 requisitos).
- Decisión de arquitectura: TCP + TLS + MySQL + bcrypt.
- Creación del repositorio en GitHub: `TsCesar/PSP-TRUCKS`.
- Estructura inicial de carpetas.

**Resultado**: Proyecto inicializado con README, .gitignore y estructura de directorios.

---

### [19-ene] Paso 1 — Arquitectura cliente-servidor base

**Objetivo**: Comunicación TCP básica con múltiples clientes.

**Actividades**:
- `server.py`: socket TCP + `threading` para múltiples clientes.
- `client.py`: cliente de consola con intérprete de comandos.
- Protocolo JSON UTF-8 con delimitador `\n`.
- Comandos de prueba: `ping`, `help`, `truck_status`, `exit`.
- Cierre limpio con `Ctrl+C` usando `threading.Event`.

**Defecto resuelto**: `KeyboardInterrupt` no siempre capturaba `accept()`. Solución: cerrar el socket desde `main()` forzando `OSError` en `accept()`.

---

### [02-feb] Paso 2 — TLS

**Objetivo**: Cifrar toda la comunicación.

**Actividades**:
- `ssl.SSLContext` en servidor y cliente.
- Certificado autofirmado RSA 4096 bits con OpenSSL.
- TLS 1.2 como versión mínima. Verificación del servidor en cliente (`CERT_REQUIRED`).

**Defecto resuelto**: `openssl` no estaba en el PATH de Windows. Solución: ruta completa de Git.

---

### [02-feb] Paso 3 — MySQL + bcrypt + autenticación

**Objetivo**: Autenticación real contra MySQL con bcrypt.

**Actividades**:
- `database.py`: conexión MySQL, consulta usuarios, registro de auditoría.
- `auth.py`: verificación con `bcrypt.checkpw()`.
- `schema.sql`: tablas `roles`, `users`, `audit_logs`.
- `seed.sql` + `tools/generate_hashes.py`.
- Variables de entorno para credenciales.

**Defectos resueltos**:
- PowerShell no soporta `<`. Solución: `Get-Content | mysql`.
- Hashes corruptos al pasar `$` en PowerShell. Solución: editar `seed.sql` en VSCode.
- XAMPP no estaba en PATH. Solución: `$env:PATH += ";C:\xampp\mysql\bin"`.

---

### [14-mar] Paso 4 — Tokens de sesión

**Objetivo**: Gestión de sesiones por token único.

**Actividades**:
- `tokens.py`: `secrets.token_hex(32)`, almacén con `threading.Lock`.
- Token generado en `auth.py` tras login exitoso.
- Cliente guarda y envía token en cada petición.
- Token revocado en logout, exit y desconexión abrupta.

**Defecto resuelto**: `getpass` congela el terminal de VSCode en Windows. Solución: `input()` con aviso de que la contraseña viaja cifrada por TLS.

---

### [14-mar] Paso 5 — RBAC

**Objetivo**: Autorización por roles.

**Actividades**:
- `rbac.py`: tabla `PERMISSIONS` con conjuntos de comandos por rol.
- `check_permission()` antes de cada comando.
- Nuevo comando `create_user` exclusivo de admin.
- Menú del cliente adaptado al rol activo.

---

### [14-mar] Paso 6 — Robustez

**Objetivo**: Sistema resistente a errores y desconexiones.

**Actividades**:
- `send_response()` tolerante a `BrokenPipeError`.
- Buffer máximo 64 KB.
- `data` forzado a `{}` si el cliente envía tipo inválido.
- `session_expired: true` en respuesta para limpieza de sesión cliente.
- Menú con 3 intentos de login con cuenta regresiva.

---

### [14-mar] Paso 7 — Auditoría completa

**Objetivo**: Registrar todos los eventos relevantes en MySQL.

**Actividades**:
- `LOGOUT` añadido en `process_message()`.
- `CLIENT_CONNECT` y `CLIENT_DISCONNECT` en `handle_client()`.
- `SERVER_ERROR` en excepción inesperada.
- Helper `_log_disconnect()` centralizado.

---

### [15-mar] Paso 8 — Gestión de flota y usuarios + documentación

**Objetivo**: Completar la funcionalidad y documentar el proyecto.

**Actividades — funcionalidad**:
- `schema.sql`: nueva tabla `trucks` (code, truck_id, description, status, location).
- `seed.sql`: 3 camiones iniciales.
- `database.py`: `get_all_trucks()`, `get_truck_by_query()`, `create_truck()`, `delete_truck()`, `get_all_users()`, `delete_user()`, `PROTECTED_USERS`.
- `rbac.py`: `add_truck` y `delete_truck` para user y admin; `delete_user` solo admin.
- `server.py`: handlers `handle_add_truck()`, `handle_delete_truck()`, `handle_delete_user()`, `handle_list_trucks()`, `handle_list_users()`; `truck_status` actualizado para consultar MySQL.
- `client.py`: `action_add_truck()`, `action_delete_truck()`, `action_delete_user()`; listas dinámicas desde servidor; `print_user_list()`.

**Actividades — documentación**:
- `docs/arquitectura.md`, `docs/protocolo.md`, `docs/seguridad.md`.
- `docs/requisitos.md`, `docs/diseno.md`, `docs/manual_usuario.md`.
- `diary/psp_log.md`.
- `memoria_tecnica.docx` para entrega en Moodle.

---

---

### [28-abr] Fase 2 — CRUD de camiones, auditoria admin y revision completa

**Objetivo**: Evolucionar la Fase 1 a un sistema de gestion de flota completo con CRUD real en MySQL, visor de auditoria para admin, y terminal mas profesional.

**Actividades — modelo de datos**:
- `schema.sql` y `seed.sql`: tabla `trucks` rediseñada (plate_number, model, capacity_kg, status ENUM, current_location, created_at, updated_at).
- `reset_trucks_phase2.sql`: script de reset seguro para migrar de Fase 1 a Fase 2 sin tocar usuarios ni auditoria.
- Constraint `CHECK (capacity_kg > 0)` y dos indices (plate_number, status) para integridad y rendimiento.

**Actividades — servidor**:
- `database.py`: funciones `update_truck()`, `get_audit_logs()`, `get_audit_logs_by_user()`, `validate_trucks_schema()`.
- `server.py`: `validate_truck_payload()` centralizado para create y update; handlers `handle_list_trucks()`, `handle_truck_detail()`, `handle_create_truck()`, `handle_update_truck()`, `handle_delete_truck()`, `handle_list_audit_logs()`, `handle_filter_audit_logs_by_user()`.
- `server.py`: `_print_server_banner()` con banner visual al arrancar mostrando host, puerto, MySQL y TLS.
- `server.py`: `raw_socket.settimeout(1.0)` para Ctrl+C limpio; `SO_REUSEADDR` ya existia.
- `rbac.py`: `list_audit_logs` y `filter_audit_logs_by_user` añadidos a permisos admin.
- `_json_default()` en `send_response()` y `_row_to_json()` en database.py para serializar objetos `datetime` de MySQL.

**Actividades — cliente**:
- `client.py`: acciones `action_list_trucks()`, `action_truck_detail()`, `action_create_truck()`, `action_update_truck()`, `action_delete_truck()`.
- `client.py`: `read_password_with_asterisks()` con msvcrt en Windows + fallback getpass.
- `client.py`: `print_audit_logs()`, `action_view_audit()` con submenu (ultimos / filtrar por usuario).
- `client.py`: `MENU_ADMIN` ampliado con opcion "Ver auditoria" (solo visible para admin).
- `client.py`: `print_header()` mejorado con doble linea de titulo, marcador de Fase 2, y rol dentro del marco.

**Actividades — documentacion**:
- `README.md`: reescrito para Fase 2 con esquema trucks correcto, comandos Fase 2, credenciales reales, ejemplos de UI.
- `docs/arquitectura.md`, `docs/protocolo.md`, `docs/seguridad.md`, `docs/requisitos.md`, `docs/diseno.md`, `docs/manual_usuario.md`: actualizados completamente para Fase 2.

**Defectos detectados y resueltos**:

| # | Descripcion | Causa | Solucion |
|---|---|---|---|
| 8 | `TypeError: Object of type datetime is not JSON serializable` | `mysql-connector-python` devuelve objetos `datetime` en columnas TIMESTAMP | `_row_to_json()` en database.py + `_json_default()` en server.py |
| 9 | `Unknown column 'plate_number' in 'field list'` | Tabla `trucks` de Fase 1 aun en MySQL | Script `reset_trucks_phase2.sql` + `validate_trucks_schema()` al arrancar |
| 10 | Ctrl+C bloqueaba el servidor indefinidamente | `accept()` bloquea el hilo sin timeout | `raw_socket.settimeout(1.0)` + captura de `socket.timeout` con `continue` |
| 11 | `handle_list_trucks` nunca detectaba error de BD | `get_all_trucks()` retornaba `[]` en error | Cambiado a retornar `None` en error y `[]` si la flota esta vacia |
| 12 | Sesion no se limpiaba si ya estaba desautenticada | `handle_server_response` tenia `and session["authenticated"]` | Eliminada la condicion redundante; siempre limpia al recibir `session_expired` |

**Decisiones tecnicas**:
- `validate_truck_payload()` centralizado evita ~25 lineas duplicadas entre create y update handlers.
- `MENU_ADMIN` separado de `MENU_USER` permite añadir opciones admin sin modificar el flujo de usuario.
- `get_all_trucks()` devuelve `None` (error BD) vs `[]` (flota vacia) para que el servidor pueda responder de forma diferente en cada caso.
- La auditoria de trucks usa eventos especificos (`TRUCK_LISTED`, `TRUCK_DETAIL`, etc.) para mayor trazabilidad, ademas del `COMMAND` generico.

---

## Resumen de tiempo estimado

| Tarea | Horas |
|---|---|
| Análisis y arquitectura base | 3 h |
| TLS y certificados | 2 h |
| MySQL + bcrypt + autenticación | 4 h |
| Tokens de sesión | 2 h |
| RBAC + create_user | 3 h |
| Robustez y UX cliente | 3 h |
| Auditoría completa | 1 h |
| Gestion de flota y usuarios (Fase 1) | 3 h |
| Documentacion Fase 1 | 3 h |
| Fase 2 — modelo datos (schema, seed, reset) | 2 h |
| Fase 2 — CRUD camiones servidor | 3 h |
| Fase 2 — CRUD camiones cliente | 3 h |
| Fase 2 — auditoria admin | 2 h |
| Fase 2 — mejoras visuales y robustez | 2 h |
| Fase 2 — documentacion | 3 h |
| **Total** | **39 h** |

---

## Defectos encontrados y resueltos

| # | Descripción | Causa | Solución |
|---|---|---|---|
| 1 | `Ctrl+C` no detenía el servidor | `accept()` bloquea el hilo | `threading.Event` + cerrar socket |
| 2 | `getpass` congela VSCode Windows | Bug del terminal integrado | Sustituir por `input()` |
| 3 | Hashes corruptos en MySQL | `$` interpretado por PowerShell | Editar SQL en VSCode, usar `Get-Content \| mysql` |
| 4 | `openssl` no reconocido | No estaba en PATH | Ruta completa de Git |
| 5 | `mysql` no reconocido | XAMPP no estaba en PATH | `$env:PATH += ";C:\xampp\mysql\bin"` |
| 6 | Buffer sin límite | Sin comprobación de tamaño | Límite 64 KB con cierre de conexión |
| 7 | Sesion cliente no se limpiaba al expirar token | Sin mecanismo de notificacion | `session_expired: true` en respuesta del servidor |
| 8 | `TypeError: datetime is not JSON serializable` | MySQL devuelve objetos datetime | `_row_to_json()` + `_json_default()` |
| 9 | `Unknown column 'plate_number'` | Tabla trucks con esquema Fase 1 | `reset_trucks_phase2.sql` + `validate_trucks_schema()` |
| 10 | Ctrl+C bloqueaba el servidor | `accept()` sin timeout | `settimeout(1.0)` + captura `socket.timeout` |
| 11 | `handle_list_trucks` no detectaba error BD | `get_all_trucks()` retornaba `[]` en error | Cambiado a retornar `None` en error |
| 12 | Sesion no se limpiaba si ya estaba desautenticada | Condicion `and session["authenticated"]` sobrante | Eliminada la condicion redundante |