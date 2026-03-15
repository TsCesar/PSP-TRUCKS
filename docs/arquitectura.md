# Arquitectura del Sistema — PSP-TRUCKS

## Descripción general

PSP-TRUCKS es una aplicación **cliente-servidor** desarrollada en Python 3 que implementa un sistema seguro de gestión de flota de transporte. La comunicación usa **sockets TCP cifrados con TLS** y los datos se persisten en **MySQL**.

---

## Diagrama de arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         PSP-TRUCKS                               │
│                                                                  │
│   ┌──────────────┐    TCP + TLS     ┌───────────────────────┐   │
│   │  Cliente CLI │ ◄──────────────► │     Servidor TCP      │   │
│   │  client.py   │   JSON / UTF-8   │     server.py         │   │
│   └──────────────┘                  │                       │   │
│                                     │  ┌─────────────────┐  │   │
│                                     │  │    auth.py      │  │   │
│                                     │  ├─────────────────┤  │   │
│                                     │  │   tokens.py     │  │   │
│                                     │  ├─────────────────┤  │   │
│                                     │  │    rbac.py      │  │   │
│                                     │  ├─────────────────┤  │   │
│                                     │  │  database.py    │  │   │
│                                     │  └────────┬────────┘  │   │
│                                     └───────────┼───────────┘   │
│                                                 ▼               │
│                                     ┌───────────────────────┐   │
│                                     │  MySQL — psp_trucks   │   │
│                                     │  roles / users /      │   │
│                                     │  trucks / audit_logs  │   │
│                                     └───────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Módulos del servidor

| Módulo | Responsabilidad |
|---|---|
| `server.py` | Sockets TCP/TLS, threading, protocolo JSON, enrutado de comandos |
| `auth.py` | Verificación de credenciales con bcrypt, generación de tokens |
| `database.py` | Consultas MySQL: usuarios, roles, camiones, auditoría |
| `tokens.py` | Almacén en memoria de tokens de sesión activos (thread-safe) |
| `rbac.py` | Tabla de permisos por rol, verificación de acceso |

## Módulo del cliente

| Módulo | Responsabilidad |
|---|---|
| `client.py` | Menú numerado interactivo, TLS, JSON, gestión de sesión y token local |

---

## Estructura de directorios

```
PSP-TRUCKS/
├── client/src/client.py
├── server/src/
│   ├── server.py
│   ├── auth.py
│   ├── database.py
│   ├── tokens.py
│   └── rbac.py
├── database/
│   ├── schema.sql        # roles, users, trucks, audit_logs
│   └── seed.sql          # datos iniciales con hashes bcrypt
├── tools/generate_hashes.py
├── certs/                # gitignored
├── docs/
└── diary/
```

---

## Modelo de base de datos

```
roles       (id PK, name UNIQUE)
users       (id PK, username UNIQUE, password_hash, role_id FK, created_at)
trucks      (id PK, code UNIQUE, truck_id UNIQUE, description, status, location, created_at)
audit_logs  (id PK, user_id FK, event_type, detail, ip_address, created_at)
```

### Tabla trucks

| Campo | Descripción |
|---|---|
| `code` | Código corto único: `T001`, `T002`... |
| `truck_id` | ID completo único: `TRUCK-001` |
| `description` | Descripción del camión |
| `status` | `available`, `in_transit`, `maintenance` |
| `location` | Ubicación actual |

---

## Concurrencia

- Cada cliente tiene su propio **hilo** (`threading.Thread`, `daemon=True`).
- El almacén de tokens usa `threading.Lock` para garantizar acceso seguro multihilo.
- El cierre con `Ctrl+C` usa `threading.Event` para notificar a todos los hilos.