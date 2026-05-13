# Modelo de Seguridad — PSP-TRUCKS Fase 2

## Resumen de capas

| Capa | Implementacion | Modulo |
|---|---|---|
| Cifrado en transito | TLS 1.2+ sobre TCP | `ssl.SSLContext` en server.py y client.py |
| Almacenamiento contrasenas | Hash bcrypt 12 rondas | `auth.py` + `database.py` |
| Autenticacion | Login MySQL + bcrypt | `auth.py` |
| Sesiones | Token criptografico en memoria | `tokens.py` |
| Autorizacion | RBAC por comando y rol | `rbac.py` |
| Proteccion admin | Usuario 'admin' no eliminable | `database.py → PROTECTED_USERS` |
| Auditoria | Registro completo en MySQL | `database.py → audit_logs` |

---

## 1. Cifrado TLS

```python
# Servidor
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_cert_chain(certfile="certs/server.crt", keyfile="certs/server.key")
raw_socket.settimeout(1.0)   # timeout para Ctrl+C limpio
server_socket = context.wrap_socket(raw_socket, server_side=True)

# Cliente
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_verify_locations(cafile="certs/server.crt")
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = False   # IP local, sin hostname DNS
```

TLS 1.0 y 1.1 rechazados. Cifrado negociado tipicamente: `TLSv1.3 — TLS_AES_256_GCM_SHA384`.
Certificado RSA 4096 bits, autofirmado. El cliente verifica el certificado del servidor.

---

## 2. bcrypt

```python
# Crear hash (create_user en server.py)
salt   = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

# Verificar (authenticate en auth.py)
bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))
```

Salt automatico por usuario, 12 rondas de coste. Tiempo constante resistente a timing attacks.
La contrasena nunca se loguea ni almacena en texto plano en ningun punto del sistema.

---

## 3. Tokens de sesion

```python
# Generacion (tokens.py)
token = secrets.token_hex(32)   # 64 chars hex — fuente SO
_store[token] = {"user_id": ..., "username": ..., "role": ..., "created_at": datetime.now()}

# Validacion en cada peticion (process_message en server.py)
session = validate_token(token)
if session is None:
    return build_response("error", "...", data={"session_expired": True}), None
```

Almacenado en memoria con `threading.Lock`. Revocado en logout, exit y desconexion abrupta.
Si el servidor se reinicia, todos los tokens se invalidan y los clientes deben hacer login.

---

## 4. RBAC — Permisos por rol

```python
PERMISSIONS = {
    "user": {
        "ping", "help", "logout",
        "list_trucks", "truck_detail", "create_truck", "update_truck", "delete_truck",
        "truck_status", "add_truck",   # aliases Fase 1
    },
    "admin": {
        "ping", "help", "logout",
        "list_trucks", "truck_detail", "create_truck", "update_truck", "delete_truck",
        "truck_status", "add_truck",
        "list_users", "create_user", "delete_user",
        "list_audit_logs", "filter_audit_logs_by_user",
    },
}
```

| Comando | user | admin |
|---|---|---|
| ping / help / logout | Si | Si |
| list_trucks / truck_detail | Si | Si |
| create_truck / update_truck / delete_truck | Si | Si |
| list_users / create_user / delete_user | No | Si |
| list_audit_logs / filter_audit_logs_by_user | No | Si |

Cada intento denegado genera un log `ACCESS_DENIED` en `audit_logs`.

---

## 5. Proteccion del administrador principal

```python
# database.py
PROTECTED_USERS = {"admin"}

def delete_user(username: str) -> dict:
    if username.lower() in {u.lower() for u in PROTECTED_USERS}:
        return {"success": False, "error": "usuario protegido"}
```

La proteccion se implementa en dos capas:
1. **Cliente**: bloquea el intento antes de enviarlo al servidor.
2. **Servidor** (`database.py → PROTECTED_USERS`): rechaza la operacion independientemente del origen.

---

## 6. Validacion de datos de entrada

Todos los datos de camiones pasan por `validate_truck_payload()` en server.py:

- `plate_number`: obligatorio, normalizado a mayusculas
- `model`: obligatorio
- `capacity_kg`: entero positivo obligatorio (CHECK en MySQL tambien)
- `status`: debe estar en `VALID_STATUSES = ("available", "in_transit", "maintenance", "inactive")`
- `current_location`: opcional, None si vacio

Mensajes de error concretos al cliente, sin exponer detalles de la BD ni del sistema.

---

## 7. Auditoria completa

| Evento | Cuando |
|---|---|
| `LOGIN_OK` / `LOGIN_FAIL` | Cada intento de autenticacion |
| `LOGOUT` | Cierre de sesion explicito |
| `COMMAND` | Cada comando ejecutado con exito |
| `ACCESS_DENIED` | Cada intento denegado por RBAC |
| `TRUCK_LISTED` | Consulta de lista de camiones |
| `TRUCK_DETAIL` | Consulta de detalle de camion |
| `TRUCK_CREATED` / `TRUCK_UPDATED` / `TRUCK_DELETED` | Operaciones CRUD |
| `USER_CREATED` / `USER_DELETED` | Alta/baja de usuarios |
| `CLIENT_CONNECT` / `CLIENT_DISCONNECT` | Cada conexion TLS |
| `SERVER_ERROR` | Excepcion inesperada en hilo |

Accesible desde el cliente (solo admin): "Ver auditoria" → subopcion "Ultimos registros" o "Filtrar por usuario".

---

## 8. Seguridad adicional

- **Buffer overflow**: conexiones con payload > 64 KB se cierran.
- **JSON invalido**: se responde con error, sin caer el proceso.
- **`data` no-dict**: se normaliza a `{}` para evitar errores de clave.
- **Anti-enumeracion**: login devuelve siempre "Credenciales incorrectas" sin especificar si falla usuario o contrasena.
- **Token no expuesto**: los logs del servidor muestran solo los primeros 8 caracteres del token.
- **Contrasena no logueada**: `action_login` y `action_create_user` usan `read_password_with_asterisks()` que muestra `*` en Windows.
