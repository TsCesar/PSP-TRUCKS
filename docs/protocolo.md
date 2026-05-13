# Protocolo de Comunicacion — PSP-TRUCKS Fase 2

## Capa de transporte

| Parametro | Valor |
|---|---|
| Protocolo | TCP (`socket.AF_INET`, `SOCK_STREAM`) |
| Host | `127.0.0.1` |
| Puerto | `12345` |
| Cifrado | TLS 1.2 minimo, negociado TLS 1.3 |
| Suite de cifrado | `TLS_AES_256_GCM_SHA384` |
| Certificado | RSA 4096 bits, autofirmado, 365 dias |

---

## Formato de mensajes

JSON codificado en UTF-8, delimitado por `\n`.

### Request sin sesion (login)

```json
{
  "type": "login",
  "data": { "username": "admin", "password": "admin123" }
}
```

### Request con sesion activa

```json
{
  "type": "list_trucks",
  "token": "<64 chars hex>",
  "data": {}
}
```

### Response exito

```json
{
  "status": "success",
  "message": "Flota — 4 camion(es) registrado(s).",
  "timestamp": "2026-04-28 23:00:00",
  "data": {
    "trucks": [
      {
        "id": 1,
        "plate_number": "1234-ABC",
        "model": "Volvo FH16",
        "capacity_kg": 24000,
        "status": "available",
        "current_location": "Leon",
        "created_at": "2026-04-28 20:00:00",
        "updated_at": "2026-04-28 20:00:00"
      }
    ]
  }
}
```

### Response error con sesion expirada

```json
{
  "status": "error",
  "message": "Sesion no valida. Inicia sesion de nuevo con 'login'.",
  "timestamp": "...",
  "data": { "session_expired": true }
}
```

---

## Tabla de comandos

| Comando | Token | Roles | Descripcion |
|---|---|---|---|
| `login` | No | Todos | Autenticacion. Devuelve token, username, role. |
| `logout` | Si | user, admin | Cierra sesion y revoca token. |
| `ping` | Si | user, admin | Comprueba conexion. Devuelve "pong". |
| `help` | Si | user, admin | Comandos disponibles para el rol activo. |
| `list_trucks` | Si | user, admin | Lista todos los camiones de la flota. |
| `truck_detail` | Si | user, admin | Detalle de un camion por matricula. |
| `create_truck` | Si | user, admin | Crea un nuevo camion. |
| `update_truck` | Si | user, admin | Modifica un camion existente. |
| `delete_truck` | Si | user, admin | Elimina un camion por matricula. |
| `list_users` | Si | admin | Lista todos los usuarios. |
| `create_user` | Si | admin | Crea un nuevo usuario. |
| `delete_user` | Si | admin | Elimina un usuario (nunca 'admin'). |
| `list_audit_logs` | Si | admin | Ultimos N registros de auditoria. |
| `filter_audit_logs_by_user` | Si | admin | Auditoria filtrada por usuario. |
| `exit` | Opcional | Todos | Desconecta el cliente, revoca token. |

*Aliases de compatibilidad: `add_truck` → `create_truck`, `truck_status` → `truck_detail`*

---

## Ejemplos de payloads

### list_trucks

```json
{
  "type": "list_trucks",
  "token": "<token>",
  "data": {}
}
```

### truck_detail

```json
{
  "type": "truck_detail",
  "token": "<token>",
  "data": { "plate_number": "1234-ABC" }
}
```

### create_truck

```json
{
  "type": "create_truck",
  "token": "<token>",
  "data": {
    "plate_number": "7777-XYZ",
    "model": "Iveco Stralis 460",
    "capacity_kg": 23000,
    "status": "available",
    "current_location": "Bilbao"
  }
}
```

### update_truck

```json
{
  "type": "update_truck",
  "token": "<token>",
  "data": {
    "plate_number": "7777-XYZ",
    "model": "Iveco Stralis 460",
    "capacity_kg": 23000,
    "status": "in_transit",
    "current_location": "Burgos"
  }
}
```

### delete_truck

```json
{
  "type": "delete_truck",
  "token": "<token>",
  "data": { "plate_number": "7777-XYZ" }
}
```

### create_user

```json
{
  "type": "create_user",
  "token": "<token>",
  "data": {
    "username": "conductor2",
    "password": "mipassword",
    "role": "user"
  }
}
```

### delete_user

```json
{
  "type": "delete_user",
  "token": "<token>",
  "data": { "username": "conductor2" }
}
```

### list_audit_logs

```json
{
  "type": "list_audit_logs",
  "token": "<token>",
  "data": { "limit": 50 }
}
```

### filter_audit_logs_by_user

```json
{
  "type": "filter_audit_logs_by_user",
  "token": "<token>",
  "data": { "username": "conductor1", "limit": 20 }
}
```

### Respuesta de auditoria

```json
{
  "status": "success",
  "message": "Auditoria — ultimos 50 registro(s).",
  "timestamp": "...",
  "data": {
    "logs": [
      {
        "id": 42,
        "username": "conductor1",
        "event_type": "LOGIN_OK",
        "detail": "Login correcto. Rol: user",
        "ip_address": "127.0.0.1:54321",
        "created_at": "2026-04-28 23:00:00"
      }
    ]
  }
}
```

---

## Gestion de errores de protocolo

| Situacion | Comportamiento |
|---|---|
| JSON invalido | Respuesta error, sin caer el servidor |
| `data` no es dict | Se normaliza a `{}` |
| Buffer > 64 KB | Cierre de conexion |
| Token invalido o ausente | Error con `session_expired: true` |
| Sin permiso RBAC | Error: permiso denegado, log ACCESS_DENIED |
| Eliminar 'admin' | Error: usuario protegido |
| `plate_number` duplicado | Error: matricula ya existe |
| `capacity_kg` no positivo | Error: debe ser entero positivo |
| `status` fuera del ENUM | Error: estado invalido |
