# 🚛 PSP-TRUCKS

<p align="center">
  <b>Sistema seguro de gestión de flota de transporte</b><br>
  <i>Aplicación cliente-servidor en Python con TLS, MySQL, bcrypt, tokens y RBAC</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/TLS-1.3-green?logo=letsencrypt&logoColor=white"/>
  <img src="https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql&logoColor=white"/>
  <img src="https://img.shields.io/badge/bcrypt-12_rounds-red"/>
  <img src="https://img.shields.io/badge/RBAC-user_/_admin-purple"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow"/>
</p>

---

## 📑 Tabla de contenidos

- [Descripción](#-descripción)
- [Arquitectura](#-arquitectura)
- [Funcionalidades](#-funcionalidades)
- [Seguridad](#-seguridad)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Modelo de datos](#-modelo-de-datos)
- [Instalación](#-instalación)
- [Ejecución](#-ejecución)
- [Uso del cliente](#-uso-del-cliente)
- [Protocolo JSON](#-protocolo-json)
- [Auditoría](#-auditoría)
- [Documentación técnica](#-documentación-técnica)
- [Metodología PSP](#-metodología-psp)

---

## 📌 Descripción

**PSP-TRUCKS** es una aplicación cliente-servidor de consola desarrollada en Python 3 para la gestión segura de una flota de camiones. El sistema implementa múltiples capas de seguridad:

- 🔐 **Canal cifrado** con TLS 1.3 en toda la comunicación
- 🔑 **Autenticación** con hash bcrypt (12 rondas) contra MySQL
- 🎫 **Sesiones** por token criptográfico único por cliente
- 👥 **Control de acceso** por roles (RBAC): `user` y `admin`
- 🚛 **Gestión de flota**: añadir, consultar y eliminar camiones
- 👤 **Gestión de usuarios**: crear y eliminar cuentas (solo admin)
- 📋 **Auditoría completa** de todos los eventos en base de datos

Desarrollado como proyecto académico del módulo **PSP (2º DAM)**, curso 2025-2026, Centro FP María Auxiliadora — León.

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                         PSP-TRUCKS                              │
│                                                                 │
│   ┌──────────────┐    TCP + TLS 1.3   ┌──────────────────────┐ │
│   │  Cliente CLI │ ◄────────────────► │    Servidor TCP      │ │
│   │  client.py   │    JSON / UTF-8    │    server.py         │ │
│   └──────────────┘                    │                      │ │
│                                       │  auth.py             │ │
│                                       │  tokens.py           │ │
│                                       │  rbac.py             │ │
│                                       │  database.py         │ │
│                                       └──────────┬───────────┘ │
│                                                  ▼             │
│                                       ┌──────────────────────┐ │
│                                       │  MySQL — psp_trucks  │ │
│                                       │  roles / users       │ │
│                                       │  trucks / audit_logs │ │
│                                       └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

El servidor acepta **múltiples clientes simultáneamente** con un hilo dedicado por conexión (`threading.Thread`). Cada cliente tiene su estado de sesión completamente independiente.

---

## ✅ Funcionalidades

### Disponibles para todos los usuarios autenticados (`user` y `admin`)

| Función | Comando | Descripción |
|---|---|---|
| Consultar camión | `truck_status` | Estado, ubicación y descripción desde MySQL |
| Añadir camión | `add_truck` | Registra nuevo camión en la flota |
| Eliminar camión | `delete_truck` | Elimina un camión por código o ID |
| Ping | `ping` | Comprueba la latencia con el servidor |
| Ayuda | `help` | Lista los comandos disponibles para el rol activo |
| Cerrar sesión | `logout` | Revoca el token en el servidor |

### Exclusivas del administrador (`admin`)

| Función | Comando | Descripción |
|---|---|---|
| Crear usuario | `create_user` | Añade un usuario con contraseña hasheada con bcrypt |
| Eliminar usuario | `delete_user` | Elimina un usuario (nunca puede eliminarse `admin`) |

### Sistema

| Función | Descripción |
|---|---|
| Login con 3 intentos | Máximo 3 intentos de autenticación antes de volver al menú |
| Menú adaptado al rol | El cliente muestra solo las opciones que el usuario puede usar |
| Pantalla limpia | Cada acción limpia la pantalla y muestra solo el resultado actual |
| Auditoría automática | Todos los eventos quedan registrados en MySQL con timestamp |

---

## 🔐 Seguridad

| Capa | Implementación | Detalle |
|---|---|---|
| **Transporte** | TLS 1.3 sobre TCP | `TLS_AES_256_GCM_SHA384` — rechaza TLS 1.0/1.1 |
| **Contraseñas** | bcrypt 12 rondas | Salt automático, tiempo constante, nunca en texto plano |
| **Sesiones** | `secrets.token_hex(32)` | 64 chars hex, fuente SO, almacén con `threading.Lock` |
| **Autorización** | RBAC por comando | `rbac.py` verifica permisos antes de ejecutar |
| **Admin protegido** | `PROTECTED_USERS` | El usuario `admin` nunca puede eliminarse |
| **Anti-enumeración** | Mensaje genérico en login | Mismo error para "usuario no existe" y "contraseña incorrecta" |
| **Buffer overflow** | Límite 64 KB | Conexiones con payload excesivo se cierran |

---

## 📂 Estructura del proyecto

```
PSP-TRUCKS/
│
├── client/
│   └── src/
│       └── client.py              # Cliente consola — menú, TLS, sesión
│
├── server/
│   └── src/
│       ├── server.py              # Servidor TCP + TLS + threading + enrutado
│       ├── auth.py                # bcrypt + generación de token
│       ├── database.py            # Consultas MySQL: users, trucks, audit
│       ├── tokens.py              # Almacén en memoria thread-safe
│       └── rbac.py                # Tabla de permisos por rol
│
├── database/
│   ├── schema.sql                 # DDL: roles, users, trucks, audit_logs
│   └── seed.sql                   # Datos iniciales con hashes bcrypt reales
│
├── tools/
│   └── generate_hashes.py         # Genera hashes bcrypt + INSERT SQL
│
├── docs/
│   ├── arquitectura.md            # Diagrama, módulos, modelo de datos
│   ├── protocolo.md               # TLS, formato JSON, tabla de comandos
│   ├── seguridad.md               # Todas las capas de seguridad
│   ├── requisitos.md              # Trazabilidad requisitos → implementación
│   ├── diseno.md                  # Decisiones de diseño y flujos
│   └── manual_usuario.md          # Instalación paso a paso y guía de uso
│
├── diary/
│   └── psp_log.md                 # Registro PSP: sesiones, tiempos, defectos
│
├── certs/                         # Certificados TLS (.gitignored)
│   ├── server.crt
│   └── server.key
│
├── logs/                          # Logs de auditoría (.gitignored)
├── .env                           # Credenciales BD (.gitignored)
├── .env.example                   # Plantilla de variables de entorno
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

---

## 🗄 Modelo de datos

### Tabla `roles`
```sql
id | name
---+-------
 1 | user
 2 | admin
```

### Tabla `users`
```sql
id | username   | password_hash        | role_id | created_at
---+------------+----------------------+---------+------------
 1 | conductor1 | $2b$12$...           | 1       | ...
 2 | admin      | $2b$12$...           | 2       | ...
```

### Tabla `trucks`
```sql
id | code | truck_id  | description                      | status      | location
---+------+-----------+----------------------------------+-------------+---------
 1 | T001 | TRUCK-001 | Camion Volvo FH16 - Base Leon    | available   | León
 2 | T002 | TRUCK-002 | Camion Scania R500 - Ruta Madrid | in_transit  | Madrid
 3 | T003 | TRUCK-003 | Camion MAN TGX - Taller Central  | maintenance | Taller Central
```

### Tabla `audit_logs`
```sql
id | user_id | event_type       | detail                          | ip_address      | created_at
---+---------+------------------+---------------------------------+-----------------+------------
 1 | 2       | LOGIN_OK         | Login correcto. Rol: admin      | 127.0.0.1:52819 | 2026-03-15 ...
 2 | 2       | COMMAND          | admin ejecutó truck_status      | 127.0.0.1:52819 | ...
 3 | 2       | TRUCK_CREATED    | admin añadió camión TRUCK-004   | ...             | ...
```

---

## ⚙ Instalación

### Requisitos previos

- Python 3.10+
- MySQL 8 / MariaDB (XAMPP recomendado en Windows)
- OpenSSL (incluido en Git para Windows)

### 1 — Clonar el repositorio

```bash
git clone https://github.com/TsCesar/PSP-TRUCKS.git
cd PSP-TRUCKS
```

### 2 — Instalar dependencias Python

```bash
pip install bcrypt mysql-connector-python
```

### 3 — Generar certificados TLS

**Linux / macOS:**
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 \
  -keyout certs/server.key -out certs/server.crt \
  -days 365 -nodes -subj "/CN=PSP-TRUCKS/O=Salesianas/C=ES"
```

**Windows (PowerShell):**
```powershell
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:4096 `
  -keyout certs/server.key -out certs/server.crt `
  -days 365 -nodes -subj "/CN=PSP-TRUCKS/O=Salesianas/C=ES"
```

### 4 — Crear la base de datos

**Linux / macOS:**
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS psp_trucks CHARACTER SET utf8mb4;"
mysql -u root -p psp_trucks < database/schema.sql
```

**Windows (PowerShell):**
```powershell
$env:PATH += ";C:\xampp\mysql\bin"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS psp_trucks CHARACTER SET utf8mb4;"
Get-Content database/schema.sql | mysql -u root psp_trucks
```

### 5 — Generar hashes bcrypt y poblar la BD

```bash
python tools/generate_hashes.py
```

El script imprime un bloque `INSERT INTO users...` con hashes bcrypt reales. Cópialo en `database/seed.sql`, reemplaza el bloque existente, guarda y ejecuta:

**Linux / macOS:**
```bash
mysql -u root -p psp_trucks < database/seed.sql
```

**Windows (PowerShell):**
```powershell
Get-Content database/seed.sql | mysql -u root psp_trucks
```

### 6 — Configurar variables de entorno

Crea un archivo `.env` en la raíz (ya incluido en `.gitignore`) o defínelas en el terminal:

**Linux / macOS:**
```bash
export DB_HOST="127.0.0.1"
export DB_NAME="psp_trucks"
export DB_USER="root"
export DB_PASSWORD="tu_contraseña"
```

**Windows (PowerShell):**
```powershell
$env:DB_HOST="127.0.0.1"
$env:DB_NAME="psp_trucks"
$env:DB_USER="root"
$env:DB_PASSWORD="tu_contraseña"
```

---

## ▶ Ejecución

```bash
# Terminal 1 — Servidor
python server/src/server.py

# Terminal 2 — Cliente
python client/src/client.py
```

**Salida esperada del servidor:**
```
[INFO] === PSP-TRUCKS Server — Fase 1 — Completo ===
[INFO] Conexión MySQL verificada — root@127.0.0.1:3306/psp_trucks
[INFO] Contexto TLS listo — certs/server.crt
[INFO] Socket TLS listo.
[INFO] Servidor TLS escuchando en 127.0.0.1:12345...
```

Para detener el servidor: **`Ctrl+C`** — el cierre es limpio.

---

## 🖥 Uso del cliente

### Pantalla inicial

```
╔══════════════════════════════════════════════╗
║          PSP-TRUCKS — Sistema de Flota       ║
╚══════════════════════════════════════════════╝
  Sin sesión activa

  Canal seguro: TLSv1.3 — TLS_AES_256_GCM_SHA384

  ── Menú ────────────────────────────────────

  [1] Iniciar sesión
  [0] Salir
```

### Menú tras login como `user`

```
  Usuario : conductor1  |  Rol : user

  [1] Ping
  [2] Estado de camión
  [3] Añadir camión
  [4] Eliminar camión
  [5] Ayuda / comandos
  [6] Cerrar sesión
  [0] Salir
```

### Menú tras login como `admin`

```
  Usuario : admin  |  Rol : admin

  [1] Ping
  [2] Estado de camión
  [3] Añadir camión
  [4] Eliminar camión
  [5] Crear usuario
  [6] Eliminar usuario
  [7] Ayuda / comandos
  [8] Cerrar sesión
  [0] Salir
```

### Estado de camión — búsqueda por código o ID

```
  ┌──────┬─────────────┬──────────────────────────────────────┐
  │ Cód  │ ID          │ Descripción                          │
  ├──────┼─────────────┼──────────────────────────────────────┤
  │ T001 │ TRUCK-001   │ Camion Volvo FH16  - Base Leon       │
  │ T002 │ TRUCK-002   │ Camion Scania R500 - Ruta Madrid     │
  │ T003 │ TRUCK-003   │ Camion MAN TGX     - Taller Central  │
  └──────┴─────────────┴──────────────────────────────────────┘

  Camión [0 para salir]: T001

  ✔  Estado de 'TRUCK-001' consultado correctamente.
  code        : T001
  truck_id    : TRUCK-001
  description : Camion Volvo FH16  - Base Leon
  status      : available
  location    : León
```

### Credenciales de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `conductor1` | `user1234` | user |
| `admin` | `admin1234` | admin |

---

## 🔄 Protocolo JSON

Todos los mensajes son objetos JSON codificados en **UTF-8**, delimitados por `\n`.

### Request autenticado

```json
{
  "type": "truck_status",
  "token": "<64 chars hex>",
  "data": { "truck_id": "T001" }
}
```

### Response de éxito

```json
{
  "status": "success",
  "message": "Estado de 'TRUCK-001' consultado correctamente.",
  "timestamp": "2026-03-15 10:00:00",
  "data": {
    "truck_id": "TRUCK-001",
    "status": "available",
    "location": "León"
  }
}
```

### Tabla completa de comandos

| Comando | Token | Roles | Descripción |
|---|---|---|---|
| `login` | No | Todos | Autenticación. Devuelve token. |
| `logout` | Sí | user, admin | Revoca token y cierra sesión. |
| `ping` | Sí | user, admin | Comprueba la conexión. |
| `help` | Sí | user, admin | Comandos disponibles para el rol. |
| `truck_status` | Sí | user, admin | Consulta estado de un camión. |
| `add_truck` | Sí | user, admin | Añade camión a la flota. |
| `delete_truck` | Sí | user, admin | Elimina camión de la flota. |
| `create_user` | Sí | admin | Crea nuevo usuario. |
| `delete_user` | Sí | admin | Elimina usuario (nunca elimina `admin`). |
| `exit` | Opcional | Todos | Desconecta el cliente. |

---

## 📋 Auditoría

Todos los eventos relevantes se registran automáticamente en la tabla `audit_logs` con `user_id`, `event_type`, `detail`, `ip_address` y `created_at`.

| Evento | Cuándo |
|---|---|
| `LOGIN_OK` / `LOGIN_FAIL` | Cada intento de autenticación |
| `COMMAND` | Cada comando ejecutado con éxito |
| `ACCESS_DENIED` | Intento denegado por RBAC |
| `USER_CREATED` / `USER_DELETED` | Alta/baja de usuarios |
| `TRUCK_CREATED` / `TRUCK_DELETED` | Alta/baja de camiones en la flota |
| `LOGOUT` | Cierre de sesión explícito |
| `CLIENT_CONNECT` / `CLIENT_DISCONNECT` | Cada conexión TLS |
| `SERVER_ERROR` | Excepción inesperada en un hilo |

**Consultar la auditoría:**

```sql
SELECT event_type, detail, ip_address, created_at
FROM audit_logs
ORDER BY created_at DESC
LIMIT 20;
```

---

## 📚 Documentación técnica

| Documento | Contenido |
|---|---|
| [`docs/arquitectura.md`](docs/arquitectura.md) | Diagrama, módulos, modelo de BD, concurrencia |
| [`docs/protocolo.md`](docs/protocolo.md) | TLS, formato JSON, tabla completa de comandos |
| [`docs/seguridad.md`](docs/seguridad.md) | Capas de seguridad con código de ejemplo |
| [`docs/requisitos.md`](docs/requisitos.md) | Trazabilidad R1–R6 + RA7 vs implementación |
| [`docs/diseno.md`](docs/diseno.md) | Decisiones de diseño y flujos de operación |
| [`docs/manual_usuario.md`](docs/manual_usuario.md) | Instalación paso a paso y guía de uso |
| [`diary/psp_log.md`](diary/psp_log.md) | Registro PSP: sesiones, tiempos y defectos |

---

## 📊 Metodología PSP

El proyecto sigue los principios del **Personal Software Process (PSP)**:

- **Registro de tiempos** por sesión de trabajo (`diary/psp_log.md`)
- **Seguimiento de defectos** con causa y solución documentadas
- **Planificación incremental** por pasos del enunciado (1 → 8)
- **Documentación estructurada** en cada módulo y a nivel de proyecto

**Tiempo total estimado**: 24 horas

---

## 🏫 Información académica

| Campo | Valor |
|---|---|
| **Módulo** | PSP — Programación de Servicios y Procesos |
| **Curso** | 2º DAM, 2025-2026 |
| **Centro** | CFP María Auxiliadora, León |
| **Peso** | 40% del módulo (RA4 + RA5) |
| **Entrega** | 15 de marzo de 2026, 23:00h |

---

## 📄 Licencia

MIT License — ver [`LICENSE`](LICENSE)