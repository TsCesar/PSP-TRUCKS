# 🚛 PSP-TRUCKS

<p align="center">
  <b>Secure Client-Server System in Python</b><br>
  <i>Academic project focused on secure distributed architecture and PSP methodology</i>
</p>

---

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Architecture](https://img.shields.io/badge/Architecture-Client--Server-informational)
![Security](https://img.shields.io/badge/TLS-Encrypted-green)
![Access](https://img.shields.io/badge/RBAC-Enabled-orange)
![Database](https://img.shields.io/badge/Database-MySQL-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

# 📑 Table of Contents

- [🇪🇸 Español](#-español)
  - Descripción
  - Arquitectura
  - Estructura del Proyecto
  - Instalación
  - Protocolo JSON
  - Modelo de Base de Datos
  - Seguridad
  - Metodología PSP
- [🇬🇧 English](#-english)
  - Description
  - Architecture
  - Project Structure
  - Installation
  - JSON Protocol
  - Database Model
  - Security
  - PSP Methodology
---

---

# 🇪🇸 Español

## 📌 Descripción del Proyecto

Sistema cliente-servidor desarrollado en Python que implementa:

- 🔐 Comunicación cifrada mediante TLS
- 👤 Autenticación obligatoria
- 👥 Control de acceso por roles (RBAC)
- 🗄 Persistencia en base de datos MySQL
- 📝 Registro de auditoría
- ⚙ Manejo robusto de errores y desconexiones

Desarrollado siguiendo principios de **Personal Software Process (PSP)**.

---

## 🏗 Arquitectura del Sistema

```
Cliente (CLI)
      │
      │  TCP + TLS
      ▼
Servidor Seguro
      │
      ▼
Base de Datos
(Usuarios - Roles - Logs)
```

---

## 📂 Estructura del Proyecto

```
PSP-TRUCKS/
│
├── client/                # Cliente CLI
│   └── client.py
│
├── server/                # Servidor TCP + TLS
│   └── server.py
│
├── database/              # Scripts SQL
│   ├── schema.sql
│   └── seed.sql
│
├── docs/                  # Documentación técnica
│   ├── requisitos.md
│   ├── diseño.md
│   └── manual_usuario.md
│
├── diary/                 # Registro PSP
│   └── psp_log.md
│
├── certs/                 # Certificados TLS
├── logs/                  # Logs de auditoría
│
├── .gitignore
├── LICENSE
└── README.md
```

---

# ⚙ Instalación Paso a Paso

## 1️⃣ Clonar repositorio

```bash
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>
```

## 2️⃣ Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3️⃣ Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4️⃣ Configurar Base de Datos

```sql
CREATE DATABASE proyecto_psp;
```

```bash
mysql -u <usuario> -p proyecto_psp < database/schema.sql
```

## 5️⃣ Generar certificados TLS

```bash
mkdir certs
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes
```

## 6️⃣ Ejecutar servidor

```bash
python server/server.py
```

## 7️⃣ Ejecutar cliente

```bash
python client/client.py
```

---

# 🔄 Protocolo de Comunicación (JSON)

Todos los mensajes utilizan formato JSON codificado en UTF-8.

### Ejemplo Login Request

```json
{
  "type": "login",
  "username": "admin",
  "password": "*****"
}
```

### Respuesta del Servidor

```json
{
  "status": "success",
  "role": "admin"
}
```

---

# 🗄 Modelo de Base de Datos

## Tabla users

- id
- username
- password_hash
- role_id

## Tabla roles

- id
- name

## Tabla audit_logs

- id
- user_id
- action
- timestamp

---

# 🔐 Modelo de Seguridad

| Capa | Implementación |
|------|---------------|
| Transporte | TLS sobre TCP |
| Credenciales | Hashing seguro |
| Autorización | RBAC |
| Auditoría | Registro persistente |
| Sesión | Gestión controlada |

---

# 📊 Metodología PSP

El proyecto incluye:

- Registro de tiempos
- Seguimiento de defectos
- Planificación incremental
- Documentación estructurada

Registros disponibles en `/diary`.

---

---

# 🇺🇸 English

## 📌 Project Description

Client-server system developed in Python that implements:

- 🔐 Encrypted communication using TLS
- 👤 Mandatory authentication
- 👥 Role-Based Access Control (RBAC)
- 🗄 MySQL database persistence
- 📝 Audit logging
- ⚙ Robust error and disconnection handling

Developed following **Personal Software Process (PSP)** principles.

---

## 🏗 System Architecture

```
Client (CLI)
      │
      │  TCP + TLS
      ▼
Secure Server
      │
      ▼
Database
(Users - Roles - Logs)
```

---

## 📂 Project Structure

```
PSP-TRUCKS/
│
├── client/                # CLI Client
│   └── client.py
│
├── server/                # TCP + TLS Server
│   └── server.py
│
├── database/              # SQL Scripts
│   ├── schema.sql
│   └── seed.sql
│
├── docs/                  # Technical Documentation
│   ├── requisitos.md
│   ├── diseño.md
│   └── manual_usuario.md
│
├── diary/                 # PSP Log
│   └── psp_log.md
│
├── certs/                 # TLS Certificates
├── logs/                  # Audit Logs
│
├── .gitignore
├── LICENSE
└── README.md
```

---

# ⚙ Step-by-Step Installation

## 1️⃣ Clone repository

```bash
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>
```

## 2️⃣ Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

## 4️⃣ Configure Database

```sql
CREATE DATABASE proyecto_psp;
```

```bash
mysql -u <usuario> -p proyecto_psp < database/schema.sql
```

## 5️⃣ Generate TLS certificates

```bash
mkdir certs
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes
```

## 6️⃣ Run server

```bash
python server/server.py
```

## 7️⃣ Run client

```bash
python client/client.py
```

---

# 🔄 Communication Protocol (JSON)

All messages use UTF-8 encoded JSON format.

### Example Login Request

```json
{
  "type": "login",
  "username": "admin",
  "password": "*****"
}
```

### Server Response

```json
{
  "status": "success",
  "role": "admin"
}
```

---

# 🗄 Database Model

## users Table

- id
- username
- password_hash
- role_id

## roles Table

- id
- name

## audit_logs Table

- id
- user_id
- action
- timestamp

---

# 🔐 Security Model

| Layer        | Implementation        |
|--------------|----------------------|
| Transport    | TLS over TCP         |
| Credentials  | Secure hashing       |
| Authorization| RBAC                 |
| Auditing     | Persistent logging   |
| Session      | Controlled management|

---

# 📊 PSP Methodology

The project includes:

- Time tracking
- Defect tracking
- Incremental planning
- Structured documentation

Logs available in `/diary`.

---

LICENSE MIT
