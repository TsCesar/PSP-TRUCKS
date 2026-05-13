# =============================================================================
# PSP-TRUCKS — Módulo de Base de Datos
# server/src/database.py
# Fase 2 — Paso 3
#
# Variables de entorno (opcional — si no se definen se usan los valores XAMPP):
#   DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASSWORD
#
# Convención de retorno en funciones de escritura:
#   {"success": True}                  → operación OK
#   {"success": False, "error": "..."}  → error controlado
#
# get_all_trucks() retorna None en error de BD y [] si la flota está vacía,
# para que el servidor pueda distinguir ambos casos.
# =============================================================================

import os
import logging
import mysql.connector
from datetime import datetime as _dt
from mysql.connector import Error as MySQLError

logger = logging.getLogger("PSP-TRUCKS-DB")

DB_CONFIG = {
    "host"    : os.getenv("DB_HOST",     "127.0.0.1"),
    "port"    : int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME",     "psp_trucks"),
    "user"    : os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

PROTECTED_USERS = {"admin"}


# -----------------------------------------------------------------------------
# Helper interno
# -----------------------------------------------------------------------------

def _row_to_json(row: dict) -> dict:
    """
    Convierte los campos datetime de una fila MySQL a string ISO
    para que json.dumps() pueda serializarlos sin TypeError.
    Aplica a created_at y updated_at devueltos por mysql-connector-python.
    """
    return {
        k: (v.strftime("%Y-%m-%d %H:%M:%S") if isinstance(v, _dt) else v)
        for k, v in row.items()
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
            f"Conexion MySQL verificada — "
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


def validate_trucks_schema() -> bool:
    """
    Verifica que la tabla trucks tiene el esquema correcto para Fase 2.
    Retorna False y loguea las columnas faltantes si el esquema es incorrecto.
    """
    REQUIRED = {
        "id", "plate_number", "model", "capacity_kg",
        "status", "current_location", "created_at", "updated_at",
    }
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'trucks'"
        )
        existing = {row[0] for row in cursor.fetchall()}
        missing  = REQUIRED - existing
        if missing:
            logger.error(
                f"Tabla 'trucks' con esquema incorrecto para Fase 2. "
                f"Columnas faltantes: {', '.join(sorted(missing))}. "
                f"Ejecuta: mysql -u root psp_trucks < database/reset_trucks_phase2.sql"
            )
            return False
        logger.info("Esquema de la tabla 'trucks' verificado.")
        return True
    except MySQLError as e:
        logger.error(f"Error al verificar esquema de trucks: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# -----------------------------------------------------------------------------
# Gestión de usuarios
# -----------------------------------------------------------------------------

def get_user_by_username(username: str) -> dict | None:
    """
    Busca un usuario por nombre.
    Retorna dict {id, username, password_hash, role} o None si no existe.
    """
    sql = """
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
        cursor.execute(sql, (username,))
        return cursor.fetchone()
    except MySQLError as e:
        logger.error(f"Error al consultar usuario '{username}': {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_role_id_by_name(role_name: str) -> int | None:
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
    Inserta un nuevo usuario. La contraseña ya llega hasheada con bcrypt.
    NUNCA se almacena ni se recibe la contraseña en texto plano aqui.
    """
    role_id = get_role_id_by_name(role_name)
    if role_id is None:
        return {"success": False, "error": f"Rol '{role_name}' no existe en la BD."}

    sql    = "INSERT INTO users (username, password_hash, role_id) VALUES (%s, %s, %s)"
    conn   = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (username, password_hash, role_id))
        conn.commit()
        logger.info(f"Usuario '{username}' creado con rol '{role_name}'.")
        return {"success": True}
    except mysql.connector.IntegrityError:
        return {"success": False, "error": f"El usuario '{username}' ya existe."}
    except MySQLError as e:
        logger.error(f"Error al crear usuario '{username}': {e}")
        return {"success": False, "error": "Error interno al crear el usuario."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_all_users() -> list:
    """
    Retorna lista de dicts {id, username, role, created_at}.
    created_at se convierte a string para ser JSON-serializable.
    Lista vacia si hay error de BD.
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
        rows = cursor.fetchall()
        return [_row_to_json(r) for r in rows]
    except MySQLError as e:
        logger.error(f"Error al obtener usuarios: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def delete_user(username: str) -> dict:
    """
    Elimina un usuario por nombre.
    Nunca elimina usuarios en PROTECTED_USERS.
    """
    if username.lower() in {u.lower() for u in PROTECTED_USERS}:
        return {"success": False,
                "error": f"El usuario '{username}' es el administrador principal y no puede eliminarse."}

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
# Gestión de camiones — modelo Fase 2
# Campos: id, plate_number, model, capacity_kg, status,
#         current_location, created_at, updated_at
# -----------------------------------------------------------------------------

def get_all_trucks() -> list | None:
    """
    Devuelve la lista completa de camiones.
    Retorna:
      list  → OK (puede ser [] si la flota esta vacia)
      None  → error de base de datos
    Los campos datetime se convierten a string para ser JSON-serializables.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, plate_number, model, capacity_kg, "
            "status, current_location, created_at, updated_at "
            "FROM trucks ORDER BY plate_number"
        )
        rows = cursor.fetchall()
        return [_row_to_json(r) for r in rows]
    except MySQLError as e:
        logger.error(f"Error al obtener camiones: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_truck_by_query(query: str) -> dict | None:
    """
    Busca un camion por matricula (insensible a mayusculas).
    Retorna dict completo del camion o None si no existe o hay error.
    Los campos datetime se convierten a string.
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, plate_number, model, capacity_kg, "
            "status, current_location, created_at, updated_at "
            "FROM trucks WHERE UPPER(plate_number) = %s LIMIT 1",
            (query.strip().upper(),)
        )
        row = cursor.fetchone()
        return _row_to_json(row) if row else None
    except MySQLError as e:
        logger.error(f"Error al buscar camion '{query}': {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def create_truck(plate_number: str, model: str, capacity_kg: int,
                 status: str = "available",
                 current_location: str = None) -> dict:
    """
    Inserta un nuevo camion. Normaliza la matricula a mayusculas.
    Retorna {"success": True} o {"success": False, "error": "..."}.
    """
    sql = (
        "INSERT INTO trucks (plate_number, model, capacity_kg, status, current_location) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (plate_number.strip().upper(), model.strip(),
                             capacity_kg, status, current_location))
        conn.commit()
        logger.info(f"Camion '{plate_number.upper()}' ({model}) creado.")
        return {"success": True}
    except mysql.connector.IntegrityError:
        return {"success": False,
                "error": f"La matricula '{plate_number.upper()}' ya existe en el sistema."}
    except MySQLError as e:
        logger.error(f"Error al crear camion '{plate_number}': {e}")
        return {"success": False, "error": "Error interno al crear el camion."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def update_truck(plate_number: str, model: str, capacity_kg: int,
                 status: str, current_location: str | None) -> dict:
    """
    Actualiza model, capacity_kg, status y current_location de un camion.
    Retorna {"success": True} o {"success": False, "error": "..."}.
    """
    sql = (
        "UPDATE trucks "
        "SET model = %s, capacity_kg = %s, status = %s, "
        "    current_location = %s, updated_at = NOW() "
        "WHERE UPPER(plate_number) = %s"
    )
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (model.strip(), capacity_kg, status,
                             current_location, plate_number.strip().upper()))
        if cursor.rowcount == 0:
            return {"success": False,
                    "error": f"Camion '{plate_number.upper()}' no encontrado."}
        conn.commit()
        logger.info(f"Camion '{plate_number.upper()}' actualizado.")
        return {"success": True}
    except MySQLError as e:
        logger.error(f"Error al actualizar camion '{plate_number}': {e}")
        return {"success": False, "error": "Error interno al actualizar el camion."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def delete_truck(query: str) -> dict:
    """
    Elimina un camion por matricula.
    Retorna {"success": True, "plate_number": "..."} o
            {"success": False, "error": "..."}.
    """
    truck = get_truck_by_query(query)
    if not truck:
        return {"success": False,
                "error": f"Camion '{query.upper()}' no encontrado."}

    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trucks WHERE id = %s", (truck["id"],))
        conn.commit()
        logger.info(f"Camion '{truck['plate_number']}' eliminado.")
        return {"success": True, "plate_number": truck["plate_number"]}
    except MySQLError as e:
        logger.error(f"Error al eliminar camion '{query}': {e}")
        return {"success": False, "error": "Error interno al eliminar el camion."}
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


# -----------------------------------------------------------------------------
# Auditoría
# -----------------------------------------------------------------------------

def log_event(event_type: str, user_id: int = None,
              detail: str = None, ip_address: str = None) -> None:
    """
    Registra un evento en audit_logs. Falla en silencio para no interrumpir el flujo.

    Tipos de evento:
      CLIENT_CONNECT / CLIENT_DISCONNECT
      LOGIN_OK / LOGIN_FAIL / LOGOUT
      COMMAND / ACCESS_DENIED / SERVER_ERROR
      TRUCK_LISTED / TRUCK_DETAIL
      TRUCK_CREATED / TRUCK_UPDATED / TRUCK_DELETED
      USER_CREATED / USER_DELETED
    """
    sql  = """
        INSERT INTO audit_logs (user_id, event_type, detail, ip_address)
        VALUES (%s, %s, %s, %s)
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, (user_id, event_type, detail, ip_address))
        conn.commit()
    except MySQLError as e:
        logger.error(f"Error al registrar auditoria ({event_type}): {e}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_audit_logs(limit: int = 50) -> list:
    """
    Devuelve los ultimos 'limit' registros de audit_logs con el username resuelto.
    Los eventos de sistema (sin user_id) muestran 'sistema' como username.
    Retorna lista vacia si hay error de BD.
    """
    sql = """
        SELECT
            a.id,
            COALESCE(u.username, 'sistema') AS username,
            a.event_type,
            a.detail,
            a.ip_address,
            a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
        LIMIT %s
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (int(limit),))
        rows = cursor.fetchall()
        logger.info(f"Auditoria consultada: {len(rows)} registro(s) (limit={limit}).")
        return [_row_to_json(r) for r in rows]
    except MySQLError as e:
        logger.error(f"Error al obtener audit_logs: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


def get_audit_logs_by_user(username: str, limit: int = 50) -> list:
    """
    Devuelve los ultimos 'limit' registros de audit_logs para el usuario indicado.
    Retorna lista vacia si no hay registros o hay error de BD.
    """
    sql = """
        SELECT
            a.id,
            COALESCE(u.username, 'sistema') AS username,
            a.event_type,
            a.detail,
            a.ip_address,
            a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE u.username = %s
        ORDER BY a.created_at DESC
        LIMIT %s
    """
    conn = cursor = None
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, (username, int(limit)))
        rows = cursor.fetchall()
        logger.info(f"Auditoria filtrada por '{username}': {len(rows)} registro(s).")
        return [_row_to_json(r) for r in rows]
    except MySQLError as e:
        logger.error(f"Error al filtrar audit_logs por '{username}': {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()
