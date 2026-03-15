# Protocolo de Comunicación — PSP-TRUCKS

## Capa de transporte

| Parámetro | Valor |
|---|---|
| Protocolo | TCP (`socket.AF_INET`, `SOCK_STREAM`) |
| Host | `127.0.0.1` |
| Puerto | `12345` |
| Cifrado | TLS 1.2 mínimo, negociado TLS 1.3 |
| Suite de cifrado | `TLS_AES_256_GCM_SHA384` |
| Certificado | RSA 4096 bits, autofirmado, 365 días |

---

## Formato de mensajes

JSON codificado en UTF-8, delimitado por `\n`.

### Request sin sesión (login)

```json
{ "type": "login", "data": { "username": "admin", "password": "admin1234" } }
```

### Request con sesión activa

```json
{ "type": "truck_status", "token": "<64 chars hex>", "data": { "truck_id": "T001" } }
```

### Response éxito

```json
{
  "status": "success",
  "message": "...",
  "timestamp": "2026-03-15 10:00:00",
  "data": { ... }
}
```

### Response error con sesión expirada

```json
{
  "status": "error",
  "message": "Sesión no válida.",
  "timestamp": "...",
  "data": { "session_expired": true }
}
```

---

## Tabla de comandos

| Comando | Token | Roles | Descripción |
|---|---|---|---|
| `login` | No | Todos | Autenticación. Devuelve token. |
| `logout` | Sí | user, admin | Cierra sesión y revoca token. |
| `ping` | Sí | user, admin | Comprueba conexión. |
| `help` | Sí | user, admin | Lista comandos del rol activo. |
| `truck_status` | Sí | user, admin | Consulta estado de un camión. |
| `add_truck` | Sí | user, admin | Añade un camión a la flota. |
| `delete_truck` | Sí | user, admin | Elimina un camión de la flota. |
| `list_trucks` | Sí | user, admin | Lista todos los camiones (uso interno del cliente). |
| `create_user` | Sí | admin | Crea un nuevo usuario. |
| `delete_user` | Sí | admin | Elimina un usuario (nunca 'admin'). |
| `list_users` | Sí | admin | Lista todos los usuarios (uso interno del cliente). |
| `exit` | Opcional | Todos | Desconecta y revoca token. |

---

## Ejemplos de payloads

### add_truck

```json
{
  "type": "add_truck",
  "token": "<token>",
  "data": {
    "code": "T004",
    "truck_id": "TRUCK-004",
    "description": "Camion Iveco Stralis - Ruta Bilbao",
    "status": "available",
    "location": "Bilbao"
  }
}
```

### delete_truck

```json
{ "type": "delete_truck", "token": "<token>", "data": { "query": "T004" } }
```

### delete_user

```json
{ "type": "delete_user", "token": "<token>", "data": { "username": "conductor1" } }
```

---

## Gestión de errores de protocolo

| Situación | Comportamiento |
|---|---|
| JSON inválido | Error sin caer el servidor |
| `data` no es dict | Se normaliza a `{}` |
| Buffer > 64 KB | Cierre de conexión |
| Token inválido | Error con `session_expired: true` |
| Sin permiso RBAC | Error con mensaje claro |
| Eliminar 'admin' | Error: usuario protegido |