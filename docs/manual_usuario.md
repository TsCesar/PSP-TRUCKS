# Manual de Usuario — PSP-TRUCKS Fase 2

## Instalacion

### Requisitos previos

- Python 3.10 o superior
- MySQL 8 / MariaDB (XAMPP recomendado en Windows)
- OpenSSL (incluido en Git para Windows)

### 1. Clonar el repositorio

```powershell
git clone https://github.com/TsCesar/PSP-TRUCKS.git
cd PSP-TRUCKS
```

### 2. Instalar dependencias Python

```powershell
pip install bcrypt mysql-connector-python
```

### 3. Generar certificados TLS

```powershell
mkdir certs
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:4096 `
    -keyout certs/server.key -out certs/server.crt `
    -days 365 -nodes -subj "/CN=PSP-TRUCKS/O=Salesianas/C=ES"
```

### 4. Crear la base de datos

Abre phpMyAdmin en `http://localhost/phpmyadmin` y crea la base `psp_trucks`, o usa la consola:

```powershell
$env:PATH += ";C:\xampp\mysql\bin"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS psp_trucks CHARACTER SET utf8mb4;"
```

### 5. Importar esquema y datos iniciales

```powershell
Get-Content database/schema.sql | mysql -u root psp_trucks
Get-Content database/seed.sql   | mysql -u root psp_trucks
```

### 6. (Solo si trucks tiene esquema de Fase 1) Reset de la tabla trucks

Si ves errores de columna al usar el servidor, ejecuta:

```powershell
Get-Content database/reset_trucks_phase2.sql | mysql -u root psp_trucks
```

El servidor tambien detecta este problema al arrancar y muestra el comando exacto.

### 7. Variables de entorno (opcional — XAMPP por defecto no necesita contrasena)

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
# Terminal 1 — Servidor (arrancar primero)
python server/src/server.py

# Terminal 2 — Cliente
python client/src/client.py
```

Para detener el servidor: **Ctrl+C** — el cierre es limpio y sin error.

---

## Credenciales de prueba

| Usuario | Contrasena | Rol |
|---|---|---|
| `conductor1` | `password123` | user |
| `admin` | `admin123` | admin |

---

## Uso del cliente

### Pantalla de conexion

Al arrancar el cliente aparece una pantalla de splash y el mensaje de conexion. Si el servidor no esta activo se muestra un error claro.

### Menu sin sesion

```
╔══════════════════════════════════════════════╗
║      PSP-TRUCKS  —  Sistema de Flota         ║
║      Fase 2  —  2 DAM  —  2025-2026         ║
╠══════════════════════════════════════════════╣
║  Sin sesion activa                           ║
╚══════════════════════════════════════════════╝

  Canal seguro: TLSv1.3 — TLS_AES_256_GCM_SHA384

  ── Menu ────────────────────────────────────

  [1] Iniciar sesion
  [0] Salir
```

### Menu rol user

```
╠══════════════════════════════════════════════╣
║  conductor1  [USER]                          ║
╚══════════════════════════════════════════════╝

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

### Menu rol admin

```
╠══════════════════════════════════════════════╣
║  admin  [ADMIN]                              ║
╚══════════════════════════════════════════════╝

  [1]  Ping
  [2]  Lista de camiones
  [3]  Detalle de camion
  [4]  Crear camion
  [5]  Modificar camion
  [6]  Eliminar camion
  [7]  Lista de usuarios
  [8]  Crear usuario
  [9]  Eliminar usuario
  [10] Ver auditoria
  [11] Ayuda / comandos
  [12] Cerrar sesion
  [0]  Salir
```

---

## Guia de opciones

### Iniciar sesion [1]

Maximo 3 intentos. Tras el tercer fallo vuelve al menu sin sesion.

```
  Intento 1 de 3

  Usuario    : admin
  Contrasena : ******** (asteriscos en Windows)

  ✔  Autenticacion correcta. Bienvenido a PSP-TRUCKS.
  Bienvenido, admin (admin)
```

### Lista de camiones [2]

Muestra todos los camiones en tiempo real desde MySQL.

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

### Detalle de camion [3]

Muestra el listado y pide la matricula. Introduce `0` para volver.

```
  Matricula del camion [0 para salir]: 1234-ABC

  ✔  Camion '1234-ABC' encontrado.
  plate_number    : 1234-ABC
  model           : Volvo FH16
  capacity_kg     : 24000
  status          : available
  current_location: Leon
```

### Crear camion [4]

```
  Matricula   (ej: 1234-ABC)     : 7777-XYZ
  Modelo      (ej: Volvo FH16)   : Iveco Stralis 460
  Capacidad   (ej: 24000) en kg  : 23000
  Estado      [Enter = available]: in_transit
  Ubicacion   [Enter = Sin asignar]: Bilbao

  ✔  Camion '7777-XYZ' creado correctamente.
```

### Modificar camion [5]

Muestra el listado, pide matricula y muestra valores actuales. Enter conserva el valor actual.

```
  Matricula del camion a modificar [0 para salir]: 7777-XYZ

  Camion: 7777-XYZ — deja en blanco para conservar el valor actual.

  Modelo      [Iveco Stralis 460]:
  Capacidad kg [23000]:
  Estado      [in_transit]: available
  Ubicacion   [Bilbao]: Valencia

  ✔  Camion '7777-XYZ' actualizado correctamente.
```

### Eliminar camion [6]

Muestra listado, pide matricula y confirmacion. Introduce `0` para volver.

```
  Matricula del camion a eliminar [0 para salir]: 7777-XYZ
  Confirmas eliminar '7777-XYZ'? (s/n): s

  ✔  Camion '7777-XYZ' eliminado correctamente.
```

### Lista de usuarios [7 — solo admin]

```
  ┌──────────────────┬─────────┐
  │ Usuario          │ Rol     │
  ├──────────────────┼─────────┤
  │ admin            │ admin   │
  │ conductor1       │ user    │
  └──────────────────┴─────────┘

  Total: 2 usuario(s) registrado(s).
```

### Crear usuario [8 — solo admin]

```
  Nuevo usuario  : conductor2
  Contrasena     : ********
  Roles disponibles: [1] user  [2] admin
  Rol [1/2 o nombre]: 1

  ✔  Usuario 'conductor2' creado correctamente con rol 'user'.
```

### Eliminar usuario [9 — solo admin]

El usuario `admin` nunca puede eliminarse.

```
  Usuario a eliminar [0 para salir]: conductor2
  Confirmas eliminar 'conductor2'? (s/n): s

  ✔  Usuario 'conductor2' eliminado correctamente.
```

### Ver auditoria [10 — solo admin]

```
  ── Auditoria del sistema [ADMIN] ───────────

  [1] Ultimos registros
  [2] Filtrar por usuario
  [0] Volver

  Opcion: 1
  Registros a mostrar [10-500, Enter=50]:

  ┌──────┬──────────────────┬──────────────────────┬────────────────────────────────────┐
  │  ID  │ Usuario          │ Evento               │ Detalle                            │
  ├──────┼──────────────────┼──────────────────────┼────────────────────────────────────┤
  │ 42   │ admin            │ LOGIN_OK             │ Login correcto. Rol: admin         │
  │ 43   │ conductor1       │ TRUCK_LISTED         │ conductor1 consulto la flota...    │
  └──────┴──────────────────┴──────────────────────┴────────────────────────────────────┘
```

---

## Verificar auditoria desde MySQL

```powershell
mysql -u root psp_trucks -e "SELECT event_type, detail, ip_address, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 20;"
```

---

## Solucion de problemas

| Error | Causa | Solucion |
|---|---|---|
| No conecta al servidor | Servidor no activo | Ejecutar `python server/src/server.py` primero |
| Certificado no valido | `server.crt` incorrecto | Usar el mismo `certs/server.crt` del servidor |
| No conecta MySQL | MySQL inactivo | Comprobar XAMPP → MySQL activo |
| Error columna en trucks | Tabla con esquema Fase 1 | `Get-Content database/reset_trucks_phase2.sql \| mysql -u root psp_trucks` |
| `openssl` no reconocido | No esta en PATH | Usar ruta completa de Git Bash |
| `mysql` no reconocido | XAMPP no esta en PATH | `$env:PATH += ";C:\xampp\mysql\bin"` |
| `<` reservado en PowerShell | Sintaxis PowerShell | Usar `Get-Content archivo.sql \| mysql ...` |
| Contrasena asteriscos no funciona | No es Windows | Se usa getpass automaticamente |
