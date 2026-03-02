# PSP-TRUCKS
🔐 Sistema cliente-servidor desarrollado en Python que implementa comunicación cifrada mediante TLS, autenticación segura, gestión de sesiones y control de acceso por roles (RBAC), con persistencia en base de datos y registro de auditoría, diseñado para aplicar buenas prácticas en seguridad y arquitectura de aplicaciones distribuidas.
🔐 Client-server system developed in Python that implements encrypted communication using TLS, secure authentication, session management, and Role-Based Access Control (RBAC), with database persistence and audit logging, designed to apply best practices in security and distributed application architecture.

🔐 Sistema Cliente-Servidor Seguro en Python
🔐 Secure Client-Server System in Python
<p align="center">












</p>
🇪🇸 ESPAÑOL
📌 Descripción del Proyecto

Este proyecto consiste en el desarrollo de una aplicación de consola basada en una arquitectura cliente-servidor, implementada íntegramente en Python, que utiliza sockets TCP con comunicaciones cifradas mediante TLS.

El sistema implementa:

Autenticación obligatoria de usuarios

Control de acceso basado en roles (RBAC)

Gestión de sesiones

Persistencia en base de datos MySQL

Registro de auditoría de eventos

Manejo robusto de errores y desconexiones

El desarrollo sigue los principios de la metodología PSP (Personal Software Process).

🎯 Objetivos Académicos

El sistema cumple con los requisitos establecidos:

✔ Aplicación cliente-servidor en consola
✔ Comunicación segura sobre TCP mediante TLS
✔ Autenticación previa antes de ejecutar comandos
✔ Gestión de roles y permisos
✔ Registro estructurado de auditoría
✔ Documentación técnica formal
✔ Organización profesional del repositorio

🏗 Arquitectura del Sistema
Cliente (CLI)
        │
        │ TCP + TLS
        ▼
Servidor Seguro
        │
        ▼
Base de Datos
(Usuarios – Roles – Logs)
🔹 Cliente

Interfaz interactiva en línea de comandos

Envía peticiones JSON al servidor

Gestiona sesión autenticada

🔹 Servidor

Escucha conexiones TCP

Establece canal cifrado TLS

Valida credenciales

Aplica control RBAC

Registra eventos en auditoría

🔹 Base de Datos

Usuarios

Roles

Hashes de contraseñas

Logs de actividad

🔐 Seguridad Implementada
🔒 Comunicación Cifrada

Uso del módulo ssl de Python para proteger la transmisión de datos.

🔑 Gestión Segura de Contraseñas

Las contraseñas se almacenan mediante hashing seguro.
No se almacenan credenciales en texto plano.

👥 Control de Acceso por Roles

Cada usuario posee un rol que determina los comandos permitidos.

📝 Auditoría

Se registran:

Intentos de autenticación

Comandos ejecutados

Accesos denegados

Errores del sistema

📂 Estructura del Repositorio
client/
server/
database/
docs/
diary/
certs/
logs/
README.md
LICENSE
.gitignore
⚙️ Instalación Paso a Paso
1️⃣ Clonar el repositorio
git clone https://github.com/<usuario>/<repositorio>.git
cd <repositorio>
2️⃣ Crear entorno virtual
Linux / macOS
python3 -m venv venv
source venv/bin/activate
Windows
python -m venv venv
.\venv\Scripts\activate
3️⃣ Instalar dependencias
pip install -r requirements.txt
4️⃣ Configurar base de datos MySQL

Crear base de datos:

CREATE DATABASE proyecto_psp;

Ejecutar esquema:

mysql -u <usuario> -p proyecto_psp < database/schema.sql

(Opcional) Cargar datos iniciales:

mysql -u <usuario> -p proyecto_psp < database/seed.sql
5️⃣ Generar certificados TLS (entorno académico)
mkdir certs
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes
6️⃣ Ejecutar servidor
python server/server.py
7️⃣ Ejecutar cliente

En otra terminal:

python client/client.py
8️⃣ Prueba de funcionamiento

Iniciar sesión

Ejecutar comando permitido

Verificar logs de auditoría

📊 Metodología PSP

El proyecto incluye:

Registro de tiempos

Seguimiento de defectos

Planificación incremental

Documentación estructurada

Los registros se encuentran en /diary.

📄 Licencia

MIT License.

🇬🇧 ENGLISH
📌 Project Overview

Console-based client-server application developed entirely in Python, using TCP sockets secured with TLS.

The system includes:

Mandatory authentication

Role-Based Access Control (RBAC)

Session management

MySQL database persistence

Audit logging

Robust error handling

Development follows Personal Software Process (PSP) principles.

🎯 Academic Objectives

✔ Console-based client-server application
✔ Secure TCP communication using TLS
✔ Authentication before command execution
✔ Role-based access control
✔ Structured audit logging
✔ Formal documentation

⚙️ Installation (Step-by-Step)
1️⃣ Clone repository
git clone https://github.com/<user>/<repo>.git
cd <repo>
2️⃣ Create virtual environment
python -m venv venv
source venv/bin/activate
3️⃣ Install dependencies
pip install -r requirements.txt
4️⃣ Configure MySQL
CREATE DATABASE proyecto_psp;
mysql -u <user> -p proyecto_psp < database/schema.sql
5️⃣ Generate TLS certificates
openssl req -x509 -newkey rsa:4096 -keyout certs/server.key -out certs/server.crt -days 365 -nodes
6️⃣ Run server
python server/server.py
7️⃣ Run client
python client/client.py
📄 License

MIT License.
