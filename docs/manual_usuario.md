# Manual de Usuario — PSP-TRUCKS

## Instalación

### Requisitos previos

- Python 3.10 o superior
- MySQL / MariaDB (XAMPP recomendado en Windows)
- OpenSSL (incluido en Git para Windows)

### 1. Clonar el repositorio

```bash
git clone https://github.com/TsCesar/PSP-TRUCKS.git
cd PSP-TRUCKS
```

### 2. Instalar dependencias Python

```powershell
pip install bcrypt mysql-connector-python
```

### 3. Generar certificados TLS

```powershell
& "C:\Program Files\Git\usr\bin\openssl.exe" req -x509 -newkey rsa:4096 `
    -keyout certs/server.key -out certs/server.crt `
    -days 365 -nodes -subj "/CN=PSP-TRUCKS/O=Salesianas/C=ES"
```

### 4. Crear la base de datos

```powershell
$env:PATH += ";C:\xampp\mysql\bin"
mysql -u root -e "CREATE DATABASE IF NOT EXISTS psp_trucks CHARACTER SET utf8mb4;"
Get-Content database/schema.sql | mysql -u root psp_trucks
```

### 5. Generar usuarios iniciales con hashes bcrypt

```powershell
python tools/generate_hashes.py
# Copia el INSERT generado → pégalo en database/seed.sql → guarda
Get-Content database/seed.sql | mysql -u root psp_trucks
```

### 6. Aplicar datos de camiones iniciales

El `seed.sql` ya incluye los 3 camiones iniciales junto con los usuarios.

### 7. Variables de entorno

```powershell
$env:DB_HOST="127.0.0.1"
$env:DB_NAME="psp_trucks"
$env:DB_USER="root"
$env:DB_PASSWORD=""
```

---

## Ejecución

```powershell
# Terminal 1 — Servidor
python server/src/server.py

# Terminal 2 — Cliente
python client/src/client.py
```

---

## Uso del cliente

### Menú sin sesión

```
  Sin sesión activa
  [1] Iniciar sesión
  [0] Salir
```

### Menú rol user

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

### Menú rol admin

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

---

## Guía de opciones

### Iniciar sesión

Máximo 3 intentos. Tras el tercer fallo vuelve al menú.

```
  Intento 1 de 3
  Usuario    : admin
  Contraseña : admin1234
  ✔  Autenticación correcta.
```

### Estado de camión [2]

Muestra el listado en tiempo real desde MySQL. Busca por código o ID. Introduce `0` para volver.

```
  ┌──────┬─────────────┬──────────────────────────────────────┐
  │ Cód  │ ID          │ Descripción                          │
  ├──────┼─────────────┼──────────────────────────────────────┤
  │ T001 │ TRUCK-001   │ Camion Volvo FH16  - Base Leon       │
  └──────┴─────────────┴──────────────────────────────────────┘
  Camión [0 para salir]: T001
  ✔  status: available  location: León
```

### Añadir camión [3]

Disponible para user y admin. Se piden: código, ID, descripción, estado y ubicación.

```
  Código corto (ej: T004): T004
  ID completo  (ej: TRUCK-004): TRUCK-004
  Descripción: Camion Iveco Stralis - Ruta Bilbao
  Estado [Enter = available]:
  Ubicación [Enter = Sin asignar]: Bilbao
  ✔  Camión 'TRUCK-004' añadido correctamente.
```

### Eliminar camión [4]

Disponible para user y admin. Muestra listado, pide código o ID y confirmación. Introduce `0` para volver.

```
  Camión a eliminar [0 para salir]: T004
  ¿Confirmas eliminar 'TRUCK-004'? (s/n): s
  ✔  Camión 'TRUCK-004' eliminado correctamente.
```

### Crear usuario [5 — solo admin]

```
  Nuevo usuario  : conductor2
  Contraseña     : mipassword
  Rol            : user
  ✔  Usuario 'conductor2' creado correctamente.
```

### Eliminar usuario [6 — solo admin]

Muestra listado de usuarios. El usuario `admin` nunca puede eliminarse.

```
  ┌──────────────────┬─────────┐
  │ Usuario          │ Rol     │
  ├──────────────────┼─────────┤
  │ admin            │ admin   │
  │ conductor1       │ user    │
  └──────────────────┴─────────┘
  Usuario [0 para salir]: conductor1
  ¿Confirmas eliminar 'conductor1'? (s/n): s
  ✔  Usuario 'conductor1' eliminado correctamente.
```

---

## Credenciales de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `conductor1` | `user1234` | user |
| `admin` | `admin1234` | admin |

---

## Verificar auditoría

```powershell
mysql -u root psp_trucks -e "SELECT event_type, detail, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 20;"
```

---

## Solución de problemas

| Error | Causa | Solución |
|---|---|---|
| No conecta al servidor | Servidor no activo | Ejecutar `python server/src/server.py` primero |
| Certificado no válido | `server.crt` incorrecto | Usar el mismo `certs/server.crt` del servidor |
| No conecta MySQL | MySQL inactivo o vars incorrectas | Comprobar XAMPP y `$env:DB_*` |
| `openssl` no reconocido | No está en PATH | Usar ruta completa de Git |
| `<` reservado PowerShell | No soportado | Usar `Get-Content archivo.sql \| mysql ...` |