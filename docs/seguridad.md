# Modelo de Seguridad — PSP-TRUCKS

## Resumen de capas

| Capa | Implementación | Módulo |
|---|---|---|
| Cifrado en tránsito | TLS 1.3 sobre TCP | `ssl.SSLContext` |
| Almacenamiento contraseñas | Hash bcrypt 12 rondas | `auth.py` + `database.py` |
| Autenticación | Login MySQL + bcrypt | `auth.py` |
| Sesiones | Token criptográfico en memoria | `tokens.py` |
| Autorización | RBAC por comando y rol | `rbac.py` |
| Protección de usuarios | Usuario 'admin' no eliminable | `database.py` |
| Auditoría | Registro completo en MySQL | `database.py` → `audit_logs` |

---

## 1. Cifrado TLS

```python
# Servidor
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_cert_chain(certfile="certs/server.crt", keyfile="certs/server.key")

# Cliente
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.load_verify_locations(cafile="certs/server.crt")
context.verify_mode = ssl.CERT_REQUIRED
```

TLS 1.0 y 1.1 rechazados. Cifrado negociado: `TLSv1.3 — TLS_AES_256_GCM_SHA384`.

---

## 2. bcrypt

```python
# Crear hash
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
# Verificar
bcrypt.checkpw(plain.encode(), stored_hash.encode())
```

Salt automático, 12 rondas de coste, tiempo constante resistente a timing attacks. La contraseña nunca se loguea ni almacena en texto plano.

---

## 3. Tokens de sesión

```python
token = secrets.token_hex(32)   # 64 chars hex — fuente SO
```

Almacenado en memoria con `threading.Lock`. Revocado en logout, exit y desconexión abrupta.

---

## 4. RBAC — Permisos por rol

```python
PERMISSIONS = {
    "user" : {"ping","help","truck_status","logout","add_truck","delete_truck"},
    "admin": {"ping","help","truck_status","logout","add_truck","delete_truck",
              "create_user","delete_user"},
}
```

| Comando | user | admin |
|---|---|---|
| `ping` / `help` | ✔ | ✔ |
| `truck_status` | ✔ | ✔ |
| `add_truck` | ✔ | ✔ |
| `delete_truck` | ✔ | ✔ |
| `create_user` | ✗ | ✔ |
| `delete_user` | ✗ | ✔ |

---

## 5. Protección del administrador principal

El usuario `admin` nunca puede eliminarse:

```python
PROTECTED_USERS = {"admin"}

def delete_user(username: str) -> dict:
    if username.lower() in {u.lower() for u in PROTECTED_USERS}:
        return {"success": False, "error": "usuario protegido"}
```

El cliente también bloquea el intento antes de enviarlo al servidor.

---

## 6. Auditoría completa

| Evento | Cuándo |
|---|---|
| `LOGIN_OK` / `LOGIN_FAIL` | Cada intento de login |
| `COMMAND` | Cada comando ejecutado con éxito |
| `ACCESS_DENIED` | Cada intento denegado por RBAC |
| `USER_CREATED` | Admin crea usuario |
| `USER_DELETED` | Admin elimina usuario |
| `TRUCK_CREATED` | Cualquier usuario añade camión |
| `TRUCK_DELETED` | Cualquier usuario elimina camión |
| `LOGOUT` | Cierre de sesión explícito |
| `CLIENT_CONNECT` | Nueva conexión TLS |
| `CLIENT_DISCONNECT` | Desconexión con motivo |
| `SERVER_ERROR` | Excepción inesperada en hilo |