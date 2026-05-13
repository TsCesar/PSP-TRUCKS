# Requisitos — PSP-TRUCKS Fase 2

---

## R1 — Programacion segura y diseno (CE a)

| Criterio | Estado | Evidencia |
|---|---|---|
| 1.1 Sin credenciales en texto plano | OK | `password_hash` en BD, `read_password_with_asterisks()` en cliente |
| 1.2 Autenticacion separada | OK | `auth.py` independiente de `server.py` |
| 1.3 Errores sin info sensible | OK | Mensajes genericos al cliente; logs tecnicos solo en servidor |
| 1.4 Codigo modularizado | OK | 5 modulos servidor + 1 cliente, responsabilidad unica por modulo |
| 1.5 Validacion de datos de entrada | OK | `validate_truck_payload()` en server.py para CRUD de camiones |
| 1.6 Esquema verificado al arrancar | OK | `validate_trucks_schema()` en database.py, llamada en main() |

## R2 — Criptografia aplicada (CE b, e)

| Criterio | Estado | Evidencia |
|---|---|---|
| 2.1 Hash seguro | OK | `bcrypt.hashpw()` con 12 rondas en `auth.py` |
| 2.2 bcrypt para verificar | OK | `bcrypt.checkpw()` con tiempo constante |
| 2.3 Sin texto plano en BD | OK | Solo `password_hash` en tabla `users` |
| 2.4 Justificacion del algoritmo | OK | Documentado en `docs/seguridad.md` |

## R3 — Autenticacion y control de acceso (CE c)

| Criterio | Estado | Evidencia |
|---|---|---|
| 3.1 Autenticacion obligatoria | OK | Barrera de token en `process_message()` antes de cualquier comando |
| 3.2 Sesiones por token | OK | `tokens.py` — `secrets.token_hex(32)`, 64 chars hex |
| 3.3 Token validado en cada peticion | OK | `validate_token()` antes de procesar todo comando |
| 3.4 Comandos sin sesion rechazados | OK | `session_expired: true` en respuesta → cliente limpia sesion |
| 3.5 Token revocado en logout y desconexion | OK | `revoke_token()` en logout, exit y `handle_client()` |
| 3.6 Maximo 3 intentos de login | OK | `MAX_LOGIN_ATTEMPTS = 3` en client.py |

## R4 — Seguridad basada en roles (CE d)

| Criterio | Estado | Evidencia |
|---|---|---|
| 4.1 Dos roles diferenciados | OK | `user` y `admin` en tabla `roles` |
| 4.2 Comandos asociados a roles | OK | `rbac.py → PERMISSIONS` con conjuntos separados |
| 4.3 Permisos verificados antes de ejecutar | OK | `check_permission()` en cada comando |
| 4.4 Acceso denegado registrado | OK | `log_event("ACCESS_DENIED")` con usuario, rol y comando |
| 4.5 Auditoria solo para admin | OK | `list_audit_logs` y `filter_audit_logs_by_user` solo en PERMISSIONS["admin"] |
| 4.6 Gestion de usuarios solo para admin | OK | `create_user`, `delete_user`, `list_users` solo para admin |

## R5 — Seguridad en transmision (CE f, g)

| Criterio | Estado | Evidencia |
|---|---|---|
| 5.1 Sockets TCP | OK | `socket.AF_INET, SOCK_STREAM` |
| 5.2 Sockets seguros SSL/TLS | OK | `ssl.SSLContext`, TLS 1.2 minimo |
| 5.3 Datos cifrados | OK | `TLSv1.3 — TLS_AES_256_GCM_SHA384` |
| 5.4 Protocolo definido y documentado | OK | JSON UTF-8 + `\n` — ver `docs/protocolo.md` |

## R6 — Persistencia y CRUD completo (CE — Fase 2)

| Criterio | Estado | Evidencia |
|---|---|---|
| 6.1 Modelo de datos Fase 2 | OK | Tabla `trucks` con 8 campos, CHECK, indices, ENUM status |
| 6.2 list_trucks | OK | `handle_list_trucks()` → `get_all_trucks()` → MySQL |
| 6.3 truck_detail | OK | `handle_truck_detail()` → `get_truck_by_query()` → MySQL |
| 6.4 create_truck | OK | `handle_create_truck()` → `create_truck()` → MySQL INSERT |
| 6.5 update_truck | OK | `handle_update_truck()` → `update_truck()` → MySQL UPDATE |
| 6.6 delete_truck | OK | `handle_delete_truck()` → `delete_truck()` → MySQL DELETE |
| 6.7 Normalizacion matricula | OK | `plate_number.upper()` en `validate_truck_payload()` |
| 6.8 Persistencia real | OK | Todos los cambios se guardan en MySQL con `conn.commit()` |

## R7 — Auditoria y trazabilidad (CE a, c)

| Criterio | Estado | Evidencia |
|---|---|---|
| 7.1 Autenticaciones registradas | OK | `LOGIN_OK` / `LOGIN_FAIL` |
| 7.2 CRUD registrado | OK | `TRUCK_LISTED`, `TRUCK_DETAIL`, `TRUCK_CREATED`, `TRUCK_UPDATED`, `TRUCK_DELETED` |
| 7.3 Gestion de usuarios registrada | OK | `USER_CREATED`, `USER_DELETED` |
| 7.4 Accesos denegados registrados | OK | `ACCESS_DENIED` con detalle de usuario y comando |
| 7.5 Logs con fecha/hora | OK | `created_at TIMESTAMP` en `audit_logs` |
| 7.6 Visor de auditoria para admin | OK | `list_audit_logs` y `filter_audit_logs_by_user` |
| 7.7 Conexiones registradas | OK | `CLIENT_CONNECT` / `CLIENT_DISCONNECT` |

## R8 — Experiencia de usuario y calidad (CE h)

| Criterio | Estado | Evidencia |
|---|---|---|
| 8.1 Menu adaptado al rol | OK | `MENU_SIN_SESION`, `MENU_USER`, `MENU_ADMIN` en client.py |
| 8.2 Mensajes de exito/error claros | OK | `print_result()` con `[OK]` / `[ERROR]` |
| 8.3 Tablas alineadas | OK | `print_truck_list()`, `print_user_list()`, `print_audit_logs()` |
| 8.4 Confirmacion antes de eliminar | OK | `input("Confirmas... (s/n)")` en delete_truck y delete_user |
| 8.5 Contrasena con asteriscos | OK | `read_password_with_asterisks()` usando msvcrt en Windows |
| 8.6 Gestion de sesion expirada | OK | `session_expired: true` limpia sesion local en handle_server_response |
| 8.7 Ctrl+C en servidor | OK | `socket.settimeout(1.0)` + `threading.Event` + handler en accept_clients |
| 8.8 Rearranque sin bloquear puerto | OK | `SO_REUSEADDR` en raw_socket |
| 8.9 Validacion de esquema al arrancar | OK | `validate_trucks_schema()` con instruccion de correccion |

---

## Funcionalidad minima obligatoria Fase 2

| Requisito | Comando | Roles |
|---|---|---|
| Autenticacion obligatoria | `login` | Todos |
| CRUD completo de camiones | `list_trucks`, `truck_detail`, `create_truck`, `update_truck`, `delete_truck` | user, admin |
| Gestion de usuarios | `list_users`, `create_user`, `delete_user` | Solo admin |
| Auditoria visible | `list_audit_logs`, `filter_audit_logs_by_user` | Solo admin |
| Gestion de errores y desconexiones | `handle_client()` con multiples handlers de excepcion | — |
| Persistencia real | Todos los cambios en MySQL via `database.py` | — |
