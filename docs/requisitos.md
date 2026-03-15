# Requisitos — PSP-TRUCKS Fase 1

---

## R1 — Programación segura y diseño (CE a)

| Criterio | Estado | Evidencia |
|---|---|---|
| 1.1 Sin credenciales en texto plano | ✅ | `password_hash` en BD, nunca logueado |
| 1.2 Autenticación separada | ✅ | `auth.py` independiente de `server.py` |
| 1.3 Errores sin info sensible | ✅ | Mensajes genéricos al cliente |
| 1.4 Código modularizado | ✅ | 5 módulos servidor + 1 cliente |

## R2 — Criptografía aplicada (CE b, e)

| Criterio | Estado | Evidencia |
|---|---|---|
| 2.1 Hash seguro | ✅ | `bcrypt.hashpw()` con 12 rondas |
| 2.2 bcrypt para verificar | ✅ | `bcrypt.checkpw()` en `auth.py` |
| 2.3 Sin texto plano en BD | ✅ | Solo `password_hash` en tabla `users` |
| 2.4 Justificación del algoritmo | ✅ | Documentado en `docs/seguridad.md` |

## R3 — Autenticación y control de acceso (CE c)

| Criterio | Estado | Evidencia |
|---|---|---|
| 3.1 Autenticación obligatoria | ✅ | Barrera de token en `process_message()` |
| 3.2 Sesiones por token | ✅ | `tokens.py` — `secrets.token_hex(32)` |
| 3.3 Token validado en cada petición | ✅ | `validate_token()` antes de procesar |
| 3.4 Comandos sin sesión rechazados | ✅ | `session_expired: true` en respuesta |

## R4 — Seguridad basada en roles (CE d)

| Criterio | Estado | Evidencia |
|---|---|---|
| 4.1 Dos roles diferenciados | ✅ | `user` y `admin` en tabla `roles` |
| 4.2 Comandos asociados a roles | ✅ | `rbac.py → PERMISSIONS` |
| 4.3 Permisos verificados antes de ejecutar | ✅ | `check_permission()` en cada comando |
| 4.4 Acceso denegado registrado | ✅ | `log_event("ACCESS_DENIED")` |

## R5 — Seguridad en transmisión (CE f, g)

| Criterio | Estado | Evidencia |
|---|---|---|
| 5.1 Sockets TCP | ✅ | `socket.AF_INET, SOCK_STREAM` |
| 5.2 Sockets seguros SSL/TLS | ✅ | `ssl.SSLContext`, TLS 1.2 mínimo |
| 5.3 Datos cifrados | ✅ | `TLSv1.3 — TLS_AES_256_GCM_SHA384` |
| 5.4 Protocolo definido y documentado | ✅ | JSON UTF-8 + `\n` — `docs/protocolo.md` |

## R6 — Auditoría y trazabilidad (CE a, c)

| Criterio | Estado | Evidencia |
|---|---|---|
| 6.1 Autenticaciones registradas | ✅ | `LOGIN_OK` / `LOGIN_FAIL` |
| 6.2 Comandos ejecutados registrados | ✅ | `COMMAND`, `TRUCK_CREATED`, `TRUCK_DELETED`, `USER_CREATED`, `USER_DELETED` |
| 6.3 Logs con fecha y hora | ✅ | `created_at TIMESTAMP` en `audit_logs` |
| 6.4 Logs con usuario y acción | ✅ | `detail` incluye `username + acción` |
| 6.5 Conexiones y desconexiones | ✅ | `CLIENT_CONNECT` / `CLIENT_DISCONNECT` |

## RA7 — Depuración y documentación (CE h)

| Criterio | Estado | Evidencia |
|---|---|---|
| 7.1 Código comentado | ✅ | Docstrings en todas las funciones |
| 7.2 Instrucciones de instalación | ✅ | `docs/manual_usuario.md` |
| 7.3 Arquitectura documentada | ✅ | `docs/arquitectura.md`, `docs/protocolo.md`, `docs/seguridad.md` |
| 7.4 Sin errores críticos | ✅ | Probado: login, logout, CRUD camiones, CRUD usuarios, desconexiones |

---

## Funcionalidad mínima obligatoria

| Requisito | Comando | Roles |
|---|---|---|
| Autenticación obligatoria | `login` | Todos |
| Comando para todos los autenticados | `truck_status`, `add_truck`, `delete_truck` | user, admin |
| Comando exclusivo para admin | `create_user`, `delete_user` | Solo admin |
| Gestión de errores y desconexiones | Manejo en `handle_client()` | — |