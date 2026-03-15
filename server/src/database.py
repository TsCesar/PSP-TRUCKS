# =============================================================================
# PSP-TRUCKS — Módulo de Base de Datos
# server/src/database.py
# Fase 1 — Paso 5
#
# Añadido respecto al Paso 4:
#   - get_role_id_by_name() → obtiene el ID de un rol por su nombre
#   - create_user()         → inserta un nuevo usuario con hash bcrypt
#
# Variables de entorno requeridas:
#   PowerShell:  $env:DB_HOST / $env:DB_NAME / $env:DB_USER / $env:DB_PASSWORD
#   Bash:        export DB_HOST / DB_NAME / DB_USER / DB_PASSWORD
# =============================================================================

import os
import logging
import mysql.connector
from mysql.connector import Error as MySQLError

logger = logging.getLogger("PSP-TRUCKS-DB")

DB_CONFIG = {
    "host"    : os.getenv("DB_HOST",     "127.0.0.1"),
    "port"    : int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME",     "psp_trucks"),
    "user"    : os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}


# -----------------------------------------------------------------------------
# Conexión
# -----------------------------------------------------------------------------

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except MySQLError as e:
        logger.error(f"Error al conectar con MySQL: {e}")
        raise


def test_connection() -> bool:
    try:
        conn = get_connection()
        conn.close()
        logger.info(
            f"Conexión MySQL verificada — "
            f"{DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}"
            f"/{DB_CONFIG['database']}"
        )
        return True
    except MySQLError:
        logger.error(
            f"No se pudo conectar a MySQL — "
            f"host: {DB_CONFIG['host']}  bd: {DB_CONFIG['database']}"
        )
        return False


# -----------------------------------------------------------------------------
# Consultas de usuarios
# -----------------------------------------------------------------------------

def get_user_by_username(username: str) -> dict | None:
    """
    Busca un usuario por nombre. Retorna dict con
    {id, username, password_hash, role} o None si no existe.
    """
    query = """
        SELECT u.id, u.username, u.password_hash, r.name AS role
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.username = %s
        LIMIT 1
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, (username,))
        return cursor.fetchone()
    except MySQLError as e:
        logger.error(f"Error al consultar usuario '{username}': {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_role_id_by_name(role_name: str) -> int | None:
    """
    Obtiene el ID de un rol por su nombre ('user' o 'admin').
    Retorna el ID o None si el rol no existe.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM roles WHERE name = %s LIMIT 1", (role_name,))
        row = cursor.fetchone()
        return row[0] if row else None
    except MySQLError as e:
        logger.error(f"Error al obtener rol '{role_name}': {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def create_user(username: str, password_hash: str, role_name: str) -> dict:
    """
    Inserta un nuevo usuario en la base de datos.

    La contraseña ya llega hasheada con bcrypt desde auth.py.
    NUNCA se almacena ni se recibe la contraseña en texto plano aquí.

    Retorna:
      {"success": True}                        → usuario creado
      {"success": False, "error": "..."}       → error (ya existe, rol inválido, etc.)
    """
    # Obtener ID del rol
    role_id = get_role_id_by_name(role_name)
    if role_id is None:
        return {"success": False, "error": f"Rol '{role_name}' no existe en la BD."}

    query  = "INSERT INTO users (username, password_hash, role_id) VALUES (%s, %s, %s)"
    conn   = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (username, password_hash, role_id))
        conn.commit()
        logger.info(f"Usuario '{username}' creado con rol '{role_name}'.")
        return {"success": True}

    except mysql.connector.IntegrityError:
        # username UNIQUE → ya existe
        return {"success": False, "error": f"El usuario '{username}' ya existe."}
    except MySQLError as e:
        logger.error(f"Error al crear usuario '{username}': {e}")
        return {"success": False, "error": "Error interno al crear el usuario."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()




# -----------------------------------------------------------------------------
# Gestión de camiones
# -----------------------------------------------------------------------------

def get_all_trucks() -> list:
    """
    Devuelve la lista completa de camiones de la flota.
    Retorna lista de dicts {id, code, truck_id, description, status, location}
    o lista vacía si hay error.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, code, truck_id, description, status, location "
            "FROM trucks ORDER BY code"
        )
        return cursor.fetchall()
    except MySQLError as e:
        logger.error(f"Error al obtener camiones: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_truck_by_query(query: str) -> dict | None:
    """
    Busca un camión por código corto (T001) o por ID completo (TRUCK-001).
    Retorna dict o None si no existe.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        # UPPER() en SQL garantiza coincidencia sin importar cómo
        # esté almacenado el valor ni la collation de la columna.
        cursor.execute(
            "SELECT id, code, truck_id, description, status, location "
            "FROM trucks WHERE UPPER(code) = %s OR UPPER(truck_id) = %s LIMIT 1",
            (query.strip().upper(), query.strip().upper())
        )
        return cursor.fetchone()
    except MySQLError as e:
        logger.error(f"Error al buscar camión '{query}': {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def create_truck(code: str, truck_id: str, description: str,
                 status: str = "available", location: str = "Sin asignar") -> dict:
    """
    Inserta un nuevo camión en la base de datos.
    Retorna {"success": True} o {"success": False, "error": "..."}.
    """
    query = ("INSERT INTO trucks (code, truck_id, description, status, location) "
             "VALUES (%s, %s, %s, %s, %s)")
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (code.upper(), truck_id.upper(), description, status, location))
        conn.commit()
        logger.info(f"Camión '{truck_id}' creado con código '{code}'.")
        return {"success": True}
    except mysql.connector.IntegrityError:
        return {"success": False, "error": f"El código '{code}' o el ID '{truck_id}' ya existe."}
    except MySQLError as e:
        logger.error(f"Error al crear camión: {e}")
        return {"success": False, "error": "Error interno al crear el camión."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def delete_truck(query: str) -> dict:
    """
    Elimina un camión por código (T001) o ID completo (TRUCK-001).
    Retorna {"success": True, "truck_id": "..."} o {"success": False, "error": "..."}.
    """
    # Primero verificar que existe
    truck = get_truck_by_query(query)
    if not truck:
        return {"success": False, "error": f"Camión '{query}' no encontrado."}

    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trucks WHERE id = %s", (truck["id"],))
        conn.commit()
        logger.info(f"Camión '{truck['truck_id']}' eliminado.")
        return {"success": True, "truck_id": truck["truck_id"], "code": truck["code"]}
    except MySQLError as e:
        logger.error(f"Error al eliminar camión '{query}': {e}")
        return {"success": False, "error": "Error interno al eliminar el camión."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# -----------------------------------------------------------------------------
# Gestión de usuarios (para el comando delete_user de admin)
# -----------------------------------------------------------------------------

PROTECTED_USERS = {"admin"}   # Usuarios que nunca se pueden eliminar

def get_all_users() -> list:
    """
    Devuelve la lista de usuarios con su rol.
    Retorna lista de dicts {id, username, role, created_at}.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT u.id, u.username, r.name AS role, u.created_at "
            "FROM users u JOIN roles r ON u.role_id = r.id "
            "ORDER BY u.username"
        )
        return cursor.fetchall()
    except MySQLError as e:
        logger.error(f"Error al obtener usuarios: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def delete_user(username: str) -> dict:
    """
    Elimina un usuario por nombre de usuario.
    Nunca permite eliminar usuarios en PROTECTED_USERS.
    Retorna {"success": True} o {"success": False, "error": "..."}.
    """
    if username.lower() in {u.lower() for u in PROTECTED_USERS}:
        return {"success": False, "error": f"El usuario '{username}' es el administrador principal y no puede eliminarse."}

    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        if cursor.rowcount == 0:
            return {"success": False, "error": f"Usuario '{username}' no encontrado."}
        conn.commit()
        logger.info(f"Usuario '{username}' eliminado.")
        return {"success": True}
    except MySQLError as e:
        logger.error(f"Error al eliminar usuario '{username}': {e}")
        return {"success": False, "error": "Error interno al eliminar el usuario."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

# -----------------------------------------------------------------------------
# Auditoría
# -----------------------------------------------------------------------------

def log_event(event_type: str, user_id: int = None,
              detail: str = None, ip_address: str = None) -> None:
    """
    Registra un evento en audit_logs. Falla en silencio.

    Tipos usados:
      LOGIN_OK / LOGIN_FAIL / COMMAND / ACCESS_DENIED / USER_CREATED
    """
    query  = """
        INSERT INTO audit_logs (user_id, event_type, detail, ip_address)
        VALUES (%s, %s, %s, %s)
    """
    conn   = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, (user_id, event_type, detail, ip_address))
        conn.commit()
    except MySQLError as e:
        logger.error(f"Error al registrar auditoría: {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()