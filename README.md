# PSP-TRUCKS

<p align="center">
  <b>Sistema seguro de gestión de flota de transporte</b><br>
  <i>Aplicación cliente-servidor en Python con TLS, MySQL, bcrypt, tokens y RBAC</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/TLS-1.2%2B-green?logo=letsencrypt&logoColor=white"/>
  <img src="https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql&logoColor=white"/>
  <img src="https://img.shields.io/badge/bcrypt-12_rounds-red"/>
  <img src="https://img.shields.io/badge/RBAC-user_/_admin-purple"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow"/>
</p>

---

## Tabla de contenidos

- [Descripcion](#descripcion)
- [Arquitectura](#arquitectura)
- [Funcionalidades](#funcionalidades)
- [Seguridad](#seguridad)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Modelo de datos](#modelo-de-datos)
- [Instalacion](#instalacion)
- [Ejecucion](#ejecucion)
- [Credenciales de prueba](#credenciales-de-prueba)
- [Uso del cliente](#uso-del-cliente)
- [Protocolo JSON](#protocolo-json)
- [Auditoria](#auditoria)
- [RBAC](#rbac)
- [Documentacion tecnica](#documentacion-tecnica)

---

## Descripcion

**PSP-TRUCKS** es una aplicacion cliente-servidor de consola desarrollada en Python 3 para la gestion segura de una flota de camiones. Implementa multiples capas de seguridad y persistencia real en MySQL/XAMPP.

**Fase 2** extiende la Fase 1 con CRUD completo de camiones, gestion de usuarios, visor de auditoria para admin, y mejoras de experiencia de usuario en cliente y servidor.

Modulo: **PSP — Programacion de Servicios y Procesos** | 2 DAM | 2025-2026 | CFP Maria Auxiliadora, Leon.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         PSP-TRUCKS                              │
│                                                                 │
│   ┌──────────────┐    TCP + TLS 1.2+   ┌──────────────────────┐│
│   │  Cliente CLI │ ◄─────────────────► │    Servidor TCP      ││
│   │  client.py   │    JSON / UTF-8     │    server.py         ││
│   └──────────────┘                     │                      ││
│                                        │  auth.py             ││
│                                        │  tokens.py           ││
│                                        │  rbac.py             ││
│                                        │  database.py         ││
│                                        └──────────┬───────────┘│
│                                                   ▼            │
│                                        ┌──────────────────────┐│
│                                        │  MySQL — psp_trucks  ││
│                                        │  roles / users       ││
│                                        │  trucks / audit_logs ││
│                                        └──────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

El servidor acepta multiples clientes simultaneos con un hilo por conexion (`threading.Thread`). Cada cliente tiene su sesion completamente independiente.

---

## Funcionalidades

### Usuarios autenticados (`user` y `admin`)

| Funcion | Comando | Descripcion |
|---|---|---|
| Listar camiones | `list_trucks` | Lista completa de la flota desde MySQL |
| Detalle de camion | `truck_detail` | Estado, modelo, capacidad y ubicacion por matricula |
| Crear camion | `create_truck` | Registra nuevo camion en la flota |
| Modificar camion | `update_truck` | Actualiza datos de un camion existente |
| Eliminar camion | `delete_truck` | Elimina un camion por matricula |
| Ping | `ping` | Comprueba la conexion con el servidor |
| Ayuda | `help` | Lista los comandos disponibles para el rol |
| Cerrar sesion | `logout` | Revoca el token en el servidor |

### Exclusivas del administrador (`admin`)

| Funcion | Comando | Descripcion |
|---|---|---|
| Listar usuarios | `list_users` | Lista todos los usuarios registrados |
| Crear usuario | `create_user` | Registra nuevo usuario con hash bcrypt |
| Eliminar usuario | `delete_user` | Elimina usuario (nunca puede eliminarse `admin`) |
| Ver auditoria | `list_audit_logs` | Ultimos N registros de auditoria |
| Filtrar auditoria | `filter_audit_logs_by_user` | Auditoria filtrada por nombre de usuario |

### Sistema

| Funcion | Descripcion |
|---|---|
| Login con 3 intentos | Maximo 3 intentos antes de volver al menu |
| Menu adaptado al rol | Solo las opciones que el rol puede usar |
| Pantalla limpia | Cada accion muestra solo su resultado |
| Auditoria automatica | Todos los eventos se registran en MySQL |
| Schema validation | El servidor verifica el esquema de trucks al arrancar |

---

## Seguridad

| Capa | Implementacion | Detalle |
|---|---|---|
| **Transporte** | TLS 1.2+ sobre TCP | `TLS_AES_256_GCM_SHA384` — rechaza TLS 1.0/1.1 |
| **Contrasenas** | bcrypt 12 rondas | Salt automatico, tiempo constante, nunca texto plano |
| **Sesiones** | `secrets.token_hex(32)` | 64 chars hex, fuente SO, almacen con `threading.Lock` |
| **Autorizacion** | RBAC por comando | `rbac.py` verifica permisos antes de ejecutar |
| **Admin protegido** | `PROTECTED_USERS` | El usuario `admin` no puede eliminarse |
| **Anti-enumeracion** | Mensaje generico en login | Mismo error para usuario y contrasena incorrectos |
| **Buffer overflow** | Limite 64 KB | Conexiones con payload excesivo se cierran |

---

## Estructura del proyecto

```
PSP-TRUCKS/
│
├── client/
│   └── src/
│       └── client.py              # Cliente consola — menu, TLS, sesion, CRUD
│
├── server/
│   └── src/
│       ├── server.py              # Servidor TCP + TLS + threading + enrutado
│       ├── auth.py                # bcrypt + generacion de token
│       ├── database.py            # Consultas MySQL: users, trucks, audit, schema check
│       ├── tokens.py              # Almacen en memoria thread-safe
│       └── rbac.py                # Tabla de permisos por rol
│
├── database/
│   ├── schema.sql                 # DDL: roles, users, trucks (Fase 2), audit_logs
│   ├── seed.sql                   # Datos iniciales con hashes bcrypt reales
│   └── reset_trucks_phase2.sql    # Reset de la tabla trucks a esquema Fase 2
│
├── tools/
│   └── generate_hashes.py         # Genera hashes bcrypt + INSERT SQL
│
├── docs/
│   ├── arquitectura.md
│   ├── protocolo.md
│   ├── seguridad.md
│   ├── requisitos.md
│   ├── diseno.md
│   └── manual_usuario.md
│
├── diary/
│   └── psp_log.md                 # Registro PSP: sesiones, tiempos, defectos
│
├── certs/                         # Certificados TLS (gitignored)
│   ├── server.crt
│   └── server.key
│
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## Modelo de datos

### Tabla `roles`
```
id | name
---+-------
 1 | user
 2 | admin
```

### Tabla `users`
```
id | username   | password_hash  | role_id | created_at
---+------------+----------------+---------+------------
 1 | conductor1 | $2b$12$...     | 1       | ...
 2 | admin      | $2b$12$...     | 2       | ...
```

### Tabla `trucks` (Fase 2)
```
id | plate_number | model              | capacity_kg | status      | current_location | created_at | updated_at
---+--------------+--------------------+-------------+-------------+------------------+------------+------------
 1 | 1234-ABC     | Volvo FH16         | 24000       | available   | Leon             | ...        | ...
 2 | 5678-DEF     | Scania R500        | 20000       | in_transit  | Madrid           | ...        | ...
 3 | 9012-GHI     | MAN TGX 26.440     | 18000       | maintenance | Taller Central   | ...        | ...
 4 | 3456-JKL     | Mercedes-Benz 2545 | 22000       | inactive    | NULL             | ...        | ...
```

### Tabla `audit_logs`
```
id | user_id | event_type   | detail                     | ip_address       | created_at
---+---------+--------------+----------------------------+------------------+------------
 1 | 2       | LOGIN_OK     | Login correcto. Rol: admin | 127.0.0.1:52819  | ...
 2 | 2       | TRUCK_LISTED | admin consulto la flota... | 127.0.0.1:52819  | ...
 3 | 2       | TRUCK_CREATED| admin creo camion ...      | ...              | ...
```

### Estados validos para trucks

| Estado | Significado |
|---|---|
| `available` | Disponible en base |
| `in_transit` | En ruta activa |
| `maintenance` | En taller o mantenimiento |
| `inactive` | Retirado o inactivo |

---

## Instalacion

### Requisitos previos

- Python 3.10+
- MySQL 8 / MariaDB (XAMPP recomendado en Windows)
- OpenSSL (incluido en Git para Windows)

### 1 — Clonar el repositorio

```powershell
git clone https://github.com/TsCesar/PSP-TRUCKS.git
cd PSP-TRUCKS
```

### 2 — Instalar dependencias Python

```powershell
pip install bcrypt mysql-connector-python
```

### 3 — Generar certificados TLS

```powershell
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:4096 `
  -keyout certs/server.key -out certs/server.crt `
  -days 365 -nodes -subj "/CN=PSP-TRUCKS/O=Salesianas/C=ES"
```

### 4 — Crear la base de datos e importar esquema

```powershell
$env:PATH += ";C:\xampp\mysql\bin"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS psp_trucks CHARACTER SET utf8mb4;"
Get-Content database/schema.sql | mysql -u root psp_trucks
Get-Content database/seed.sql   | mysql -u root psp_trucks
```

### 5 — (Solo si trucks tiene esquema antiguo) Reset de la tabla trucks

Si la tabla `trucks` tiene columnas de Fase 1 (`code`, `truck_id`, `description`):

```powershell
Get-Content database/reset_trucks_phase2.sql | mysql -u root psp_trucks
```

El servidor tambien verifica el esquema al arrancar y muestra el comando exacto si detecta un problema.

### 6 — Variables de entorno (solo si no usas XAMPP por defecto)

```powershell
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="3306"
$env:DB_NAME="psp_trucks"
$env:DB_USER="root"
$env:DB_PASSWORD=""
```

---

## Ejecucion

```powershell
# Terminal 1 — Servidor
python server/src/server.py

# Terminal 2 — Cliente (otra terminal)
python client/src/client.py
```

**Salida esperada del servidor:**

```
  ╔══════════════════════════════════════════════════════╗
  ║            PSP-TRUCKS  —  Servidor de Flota          ║
  ║            Fase 2  —  2 DAM  —  2025-2026           ║
  ╠══════════════════════════════════════════════════════╣
  ║  Escuchando  : 127.0.0.1:12345                       ║
  ║  MySQL       : root@127.0.0.1:3306/psp_trucks        ║
  ║  TLS         : habilitado (RSA 4096, min. TLS 1.2)   ║
  ║  Parada      : Ctrl+C                                ║
  ╚══════════════════════════════════════════════════════╝

[INFO] Conexion MySQL verificada
[INFO] Esquema de la tabla 'trucks' verificado.
[INFO] Contexto TLS listo
[INFO] Servidor TLS escuchando en 127.0.0.1:12345...
```

Para detener el servidor: **`Ctrl+C`** — el cierre es limpio.

---

## Credenciales de prueba

| Usuario | Contrasena | Rol |
|---|---|---|
| `conductor1` | `password123` | user |
| `admin` | `admin123` | admin |

---

## Uso del cliente

### Pantalla inicial

```
  ╔══════════════════════════════════════════════╗
  ║       PSP-TRUCKS  —  Sistema de Flota        ║
  ║       Fase 2  —  2 DAM  —  2025-2026        ║
  ╠══════════════════════════════════════════════╣
  ║  Sin sesion activa                           ║
  ╚══════════════════════════════════════════════╝

  Canal seguro: TLSv1.3 — TLS_AES_256_GCM_SHA384

  ── Menu ────────────────────────────────────

  [1] Iniciar sesion
  [0] Salir
```

### Menu tras login como `user`

```
  ║  conductor1  [USER]                          ║

  [1] Ping
  [2] Lista de camiones
  [3] Detalle de camion
  [4] Crear camion
  [5] Modificar camion
  [6] Eliminar camion
  [7] Ayuda / comandos
  [8] Cerrar sesion
  [0] Salir
```

### Menu tras login como `admin`

```
  ║  admin  [ADMIN]                              ║

  [1] Ping
  [2] Lista de camiones
  [3] Detalle de camion
  [4] Crear camion
  [5] Modificar camion
  [6] Eliminar camion
  [7] Lista de usuarios
  [8] Crear usuario
  [9] Eliminar usuario
  [10] Ver auditoria
  [11] Ayuda / comandos
  [12] Cerrar sesion
  [0] Salir
```

### Lista de camiones

```
  ┌──────────────┬──────────────────────┬───────────┬─────────────┬─────────────────┐
  │ Matricula    │ Modelo               │ Cap. (kg) │ Estado      │ Ubicacion       │
  ├──────────────┼──────────────────────┼───────────┼─────────────┼─────────────────┤
  │ 1234-ABC     │ Volvo FH16           │     24000 │ available   │ Leon            │
  │ 3456-JKL     │ Mercedes-Benz 2545   │     22000 │ inactive    │                 │
  │ 5678-DEF     │ Scania R500          │     20000 │ in_transit  │ Madrid          │
  │ 9012-GHI     │ MAN TGX 26.440       │     18000 │ maintenance │ Taller Central  │
  └──────────────┴──────────────────────┴───────────┴─────────────┴─────────────────┘

  Total: 4 camion(es) registrado(s).
```

---

## Protocolo JSON

Todos los mensajes son objetos JSON codificados en **UTF-8**, delimitados por `\n`.

### Request de login

```json
{ "type": "login", "data": { "username": "admin", "password": "admin123" } }
```

### Request autenticado

```json
{ "type": "list_trucks", "token": "<64 chars hex>", "data": {} }
```

### Response de exito

```json
{
  "status": "success",
  "message": "Flota — 4 camion(es) registrado(s).",
  "timestamp": "2026-04-28 23:00:00",
  "data": {
    "trucks": [...]
  }
}
```

### Response con sesion expirada

```json
{
  "status": "error",
  "message": "Sesion no valida. Inicia sesion de nuevo.",
  "timestamp": "...",
  "data": { "session_expired": true }
}
```

### Tabla completa de comandos

| Comando | Token | Roles | Descripcion |
|---|---|---|---|
| `login` | No | Todos | Autenticacion. Devuelve token. |
| `logout` | Si | user, admin | Revoca token y cierra sesion. |
| `ping` | Si | user, admin | Comprueba la conexion. |
| `help` | Si | user, admin | Comandos disponibles para el rol. |
| `list_trucks` | Si | user, admin | Lista todos los camiones. |
| `truck_detail` | Si | user, admin | Detalle de un camion por matricula. |
| `create_truck` | Si | user, admin | Crea un nuevo camion. |
| `update_truck` | Si | user, admin | Modifica un camion existente. |
| `delete_truck` | Si | user, admin | Elimina un camion por matricula. |
| `list_users` | Si | admin | Lista todos los usuarios. |
| `create_user` | Si | admin | Crea un nuevo usuario. |
| `delete_user` | Si | admin | Elimina un usuario (nunca `admin`). |
| `list_audit_logs` | Si | admin | Ultimos N registros de auditoria. |
| `filter_audit_logs_by_user` | Si | admin | Auditoria filtrada por usuario. |
| `exit` | Opcional | Todos | Desconecta el cliente. |

---

## Auditoria

Todos los eventos relevantes se registran automaticamente en `audit_logs`.

| Evento | Cuando |
|---|---|
| `LOGIN_OK` / `LOGIN_FAIL` | Cada intento de autenticacion |
| `LOGOUT` | Cierre de sesion explicito |
| `COMMAND` | Cada comando ejecutado con exito |
| `ACCESS_DENIED` | Intento denegado por RBAC |
| `TRUCK_LISTED` / `TRUCK_DETAIL` | Consulta de flota o camion individual |
| `TRUCK_CREATED` / `TRUCK_UPDATED` / `TRUCK_DELETED` | Operaciones CRUD sobre camiones |
| `USER_CREATED` / `USER_DELETED` | Alta/baja de usuarios |
| `CLIENT_CONNECT` / `CLIENT_DISCONNECT` | Cada conexion TLS |
| `SERVER_ERROR` | Excepcion inesperada en un hilo |

El admin puede consultar la auditoria directamente desde el cliente (opcion "Ver auditoria").

---

## RBAC

| Comando | user | admin |
|---|---|---|
| ping / help / logout | Si | Si |
| list_trucks / truck_detail | Si | Si |
| create_truck / update_truck / delete_truck | Si | Si |
| list_users / create_user / delete_user | No | Si |
| list_audit_logs / filter_audit_logs_by_user | No | Si |

---

## Documentacion tecnica

| Documento | Contenido |
|---|---|
| [`docs/arquitectura.md`](docs/arquitectura.md) | Diagrama, modulos, modelo de BD, concurrencia |
| [`docs/protocolo.md`](docs/protocolo.md) | TLS, formato JSON, tabla de comandos, ejemplos |
| [`docs/seguridad.md`](docs/seguridad.md) | Capas de seguridad con codigo de ejemplo |
| [`docs/requisitos.md`](docs/requisitos.md) | Trazabilidad requisitos vs implementacion Fase 2 |
| [`docs/diseno.md`](docs/diseno.md) | Decisiones de diseno y flujos de operacion |
| [`docs/manual_usuario.md`](docs/manual_usuario.md) | Instalacion paso a paso y guia de uso |
| [`diary/psp_log.md`](diary/psp_log.md) | Registro PSP: sesiones, tiempos y defectos |

---

## Informacion academica

| Campo | Valor |
|---|---|
| **Modulo** | PSP — Programacion de Servicios y Procesos |
| **Curso** | 2 DAM, 2025-2026 |
| **Centro** | CFP Maria Auxiliadora, Leon |
| **Alumno** | Cesar Mendez |

---

## Licencia

MIT License — ver [`LICENSE`](LICENSE)
