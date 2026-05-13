# Arquitectura del Sistema — PSP-TRUCKS Fase 2

## Descripcion general

PSP-TRUCKS es una aplicacion **cliente-servidor** desarrollada en Python 3 que implementa un sistema seguro de gestion de flota de transporte. La comunicacion usa **sockets TCP cifrados con TLS** y los datos persisten en **MySQL** via XAMPP.

---

## Diagrama de arquitectura

```
┌──────────────────────────────────────────────────────────────────┐
│                         PSP-TRUCKS                               │
│                                                                  │
│   ┌──────────────┐    TCP + TLS 1.2+    ┌────────────────────┐  │
│   │  Cliente CLI │ ◄──────────────────► │   Servidor TCP     │  │
│   │  client.py   │    JSON / UTF-8      │   server.py        │  │
│   └──────────────┘                      │                    │  │
│                                         │  ┌──────────────┐  │  │
│                                         │  │  auth.py     │  │  │
│                                         │  ├──────────────┤  │  │
│                                         │  │  tokens.py   │  │  │
│                                         │  ├──────────────┤  │  │
│                                         │  │  rbac.py     │  │  │
│                                         │  ├──────────────┤  │  │
│                                         │  │  database.py │  │  │
│                                         │  └──────┬───────┘  │  │
│                                         └─────────┼──────────┘  │
│                                                   ▼             │
│                                         ┌──────────────────────┐│
│                                         │  MySQL — psp_trucks  ││
│                                         │  roles / users /     ││
│                                         │  trucks / audit_logs ││
│                                         └──────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Modulos del servidor

| Modulo | Responsabilidad |
|---|---|
| `server.py` | Sockets TCP/TLS, threading, protocolo JSON, enrutado de comandos, banner de inicio |
| `auth.py` | Verificacion de credenciales con bcrypt, generacion de tokens |
| `database.py` | Consultas MySQL: usuarios, roles, camiones, auditoria, validacion de esquema |
| `tokens.py` | Almacen en memoria de tokens de sesion activos (thread-safe) |
| `rbac.py` | Tabla de permisos por rol, verificacion de acceso |

## Modulo del cliente

| Modulo | Responsabilidad |
|---|---|
| `client.py` | Menu interactivo, TLS, JSON, sesion, CRUD camiones, CRUD usuarios, visor auditoria |

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
│   ├── schema.sql                  # DDL completo
│   ├── seed.sql                    # Datos iniciales
│   └── reset_trucks_phase2.sql     # Reset tabla trucks a Fase 2
├── tools/generate_hashes.py
├── certs/                          # gitignored
├── docs/
└── diary/
```

---

## Modelo de base de datos

```
roles       (id PK, name UNIQUE)
users       (id PK, username UNIQUE, password_hash, role_id FK, created_at)
trucks      (id PK, plate_number UNIQUE, model, capacity_kg, status ENUM,
             current_location, created_at, updated_at)
audit_logs  (id PK, user_id FK, event_type, detail, ip_address, created_at)
```

### Tabla trucks — Fase 2

| Campo | Tipo | Descripcion |
|---|---|---|
| `plate_number` | VARCHAR(20) UNIQUE | Matricula del camion (ej. "1234-ABC"), normalizada a mayusculas |
| `model` | VARCHAR(100) | Marca y modelo (ej. "Volvo FH16") |
| `capacity_kg` | INT | Capacidad maxima en kg (entero positivo, CHECK > 0) |
| `status` | ENUM | `available`, `in_transit`, `maintenance`, `inactive` |
| `current_location` | VARCHAR(100) | Ubicacion actual, nullable |
| `created_at` | TIMESTAMP | Fecha de alta, automatica |
| `updated_at` | TIMESTAMP | Ultima modificacion, automatica (ON UPDATE) |

---

## Concurrencia

- Cada cliente tiene su propio **hilo** (`threading.Thread`, `daemon=True`).
- El almacen de tokens usa `threading.Lock` para garantizar acceso seguro multihilo.
- El cierre con `Ctrl+C` usa `threading.Event` para notificar al bucle de aceptacion.
- El socket de escucha tiene `settimeout(1.0)` para que el bucle compruebe el evento cada segundo.
- `SO_REUSEADDR` en el socket para rearrancar inmediatamente sin esperar TIME_WAIT.

---

## Flujo de arranque del servidor

```
main()
  ├── _print_server_banner()          → banner visual en consola
  ├── test_connection()               → verifica MySQL disponible
  ├── validate_trucks_schema()        → verifica columnas Fase 2 en trucks
  ├── create_ssl_context()            → carga certificado TLS
  ├── socket.socket() + settimeout()  → socket TCP con timeout
  └── accept_clients(shutdown_event)  → bucle de aceptacion
```

---

## Flujo de autenticacion y autorizacion

```
cliente envia {"type": "login", "data": {...}}
  └── handle_login()
        └── authenticate()
              ├── get_user_by_username()   → MySQL
              ├── verify_password()        → bcrypt.checkpw()
              └── generate_token()         → secrets.token_hex(32)

cliente envia {"type": "list_trucks", "token": "...", "data": {}}
  └── process_message()
        ├── validate_token()   → tokens.py
        ├── check_permission() → rbac.py
        └── handle_list_trucks() → database.py → MySQL
```
