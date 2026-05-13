# =============================================================================
# PSP-TRUCKS — Servidor TCP + TLS + Auth + Tokens + RBAC
# server/src/server.py
# Fase 2 — Paso 3
#
# Eventos auditados en audit_logs:
#   CLIENT_CONNECT / CLIENT_DISCONNECT
#   LOGIN_OK / LOGIN_FAIL  → auth.py
#   LOGOUT
#   COMMAND                → log generico tras cada comando exitoso
#   ACCESS_DENIED          → RBAC deniega el comando
#   SERVER_ERROR           → excepcion inesperada en hilo
#   TRUCK_LISTED           → list_trucks
#   TRUCK_DETAIL           → truck_detail / truck_status
#   TRUCK_CREATED          → create_truck / add_truck
#   TRUCK_UPDATED          → update_truck
#   TRUCK_DELETED          → delete_truck
#   USER_CREATED           → create_user
#   USER_DELETED           → delete_user
#
# Modulos:
#   server.py   → sockets, TLS, protocolo, enrutado
#   rbac.py     → tabla de permisos y verificacion
#   auth.py     → bcrypt + generate_token + hash_password
#   tokens.py   → almacen en memoria
#   database.py → MySQL / XAMPP
# =============================================================================

import ssl
import os
import sys
import socket
import threading
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth     import authenticate, hash_password
from database import (DB_CONFIG,
                       test_connection, validate_trucks_schema,
                       log_event, create_user,
                       get_all_trucks, get_truck_by_query,
                       create_truck, update_truck, delete_truck,
                       get_all_users, delete_user,
                       get_audit_logs, get_audit_logs_by_user)
from tokens   import validate_token, revoke_token, active_count
from rbac     import check_permission, PERMISSIONS

# -----------------------------------------------------------------------------
# Configuracion
# -----------------------------------------------------------------------------

HOST        = "127.0.0.1"
PORT        = 12345
BUFFER_SIZE = 4096
ENCODING    = "utf-8"
MAX_BUFFER  = BUFFER_SIZE * 16   # 64 KB — proteccion contra desbordamiento

VALID_STATUSES = ("available", "in_transit", "maintenance", "inactive")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CERT_FILE = os.path.join(BASE_DIR, "certs", "server.crt")
KEY_FILE  = os.path.join(BASE_DIR, "certs", "server.key")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PSP-TRUCKS-Server")


# -----------------------------------------------------------------------------
# TLS
# -----------------------------------------------------------------------------

def create_ssl_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if not os.path.isfile(CERT_FILE):
        raise FileNotFoundError(
            f"Certificado no encontrado: {CERT_FILE}\n"
            f"  openssl req -x509 -newkey rsa:4096 -keyout certs/server.key "
            f"-out certs/server.crt -days 365 -nodes"
        )
    if not os.path.isfile(KEY_FILE):
        raise FileNotFoundError(f"Clave privada no encontrada: {KEY_FILE}")
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    logger.info(f"Contexto TLS listo — {CERT_FILE}")
    return context


# -----------------------------------------------------------------------------
# Banner de inicio
# -----------------------------------------------------------------------------

def _print_server_banner() -> None:
    W  = 54
    db = DB_CONFIG
    db_str = f"{db['user']}@{db['host']}:{db['port']}/{db['database']}"
    host_str = f"{HOST}:{PORT}"
    print()
    print(f"  ╔{'═' * W}╗")
    print(f"  ║{'PSP-TRUCKS  —  Servidor de Flota':^{W}}║")
    print(f"  ║{'Fase 2  —  2 DAM  —  2025-2026':^{W}}║")
    print(f"  ╠{'═' * W}╣")
    print(f"  ║  {'Escuchando':<12}: {host_str:<{W - 16}}║")
    print(f"  ║  {'MySQL':<12}: {db_str:<{W - 16}}║")
    print(f"  ║  {'TLS':<12}: {'habilitado (RSA 4096, min. TLS 1.2)':<{W - 16}}║")
    print(f"  ║  {'Parada':<12}: {'Ctrl+C':<{W - 16}}║")
    print(f"  ╚{'═' * W}╝")
    print()


# -----------------------------------------------------------------------------
# Serializacion y respuestas
# -----------------------------------------------------------------------------

def _json_default(obj):
    """Fallback para json.dumps: convierte datetime a string si alguno escapa a la BD."""
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    raise TypeError(f"Tipo no serializable por JSON: {type(obj)}")


def build_response(status: str, message: str, data: dict = None) -> dict:
    response = {
        "status"   : status,
        "message"  : message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if data is not None:
        response["data"] = data
    return response


def send_response(conn: ssl.SSLSocket, response: dict) -> bool:
    """
    Serializa y envia la respuesta JSON al cliente.
    Usa _json_default para manejar datetime que puedan venir de la BD.
    Retorna True si el envio fue exitoso.
    """
    try:
        raw = json.dumps(response, ensure_ascii=False, default=_json_default) + "\n"
        conn.sendall(raw.encode(ENCODING))
        return True
    except (BrokenPipeError, OSError):
        return False
    except Exception as e:
        logger.error(f"Error al enviar respuesta: {e}")
        return False


# -----------------------------------------------------------------------------
# Handlers de comandos — usuarios
# -----------------------------------------------------------------------------

def handle_login(data: dict, client_addr: tuple) -> dict:
    """Login — no requiere token ni permisos previos."""
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return build_response("error", "Se requieren 'username' y 'password'.")

    ip_str      = f"{client_addr[0]}:{client_addr[1]}"
    auth_result = authenticate(username, password, ip_address=ip_str)

    if auth_result["success"]:
        logger.info(
            f"[{client_addr}] Sesion iniciada — "
            f"'{username}' (rol: {auth_result['role']}) "
            f"token: {auth_result['token'][:8]}..."
        )
        return build_response(
            "success",
            "Autenticacion correcta. Bienvenido a PSP-TRUCKS.",
            data={
                "username": auth_result["username"],
                "role"    : auth_result["role"],
                "token"   : auth_result["token"],
            }
        )
    return build_response("error", "Credenciales incorrectas.")


def handle_create_user(data: dict, session: dict, ip_str: str) -> dict:
    """Crea un nuevo usuario — exclusivo del rol admin."""
    new_username = data.get("username", "").strip()
    new_password = data.get("password", "")
    new_role     = data.get("role", "user").strip().lower()

    if not new_username or not new_password:
        return build_response("error", "Se requieren 'username' y 'password'.")

    if new_role not in ("user", "admin"):
        return build_response("error", "El rol debe ser 'user' o 'admin'.")

    password_hash = hash_password(new_password)
    result        = create_user(new_username, password_hash, new_role)

    if result["success"]:
        log_event(
            "USER_CREATED",
            user_id    = session["user_id"],
            detail     = f"Admin '{session['username']}' creo usuario '{new_username}' (rol: {new_role})",
            ip_address = ip_str,
        )
        return build_response(
            "success",
            f"Usuario '{new_username}' creado correctamente con rol '{new_role}'.",
        )
    return build_response("error", result["error"])


def handle_delete_user(data: dict, session: dict, ip_str: str) -> dict:
    """Elimina un usuario del sistema. Exclusivo de admin."""
    username = data.get("username", "").strip()
    if not username:
        return build_response("error", "Se requiere el campo 'username'.")

    if username.lower() == session["username"].lower():
        return build_response("error", "No puedes eliminar tu propio usuario.")

    result = delete_user(username)
    if result["success"]:
        log_event(
            "USER_DELETED",
            user_id    = session["user_id"],
            detail     = f"Admin '{session['username']}' elimino usuario '{username}'",
            ip_address = ip_str,
        )
        return build_response("success", f"Usuario '{username}' eliminado correctamente.")
    return build_response("error", result["error"])


def handle_list_users(session: dict) -> dict:
    """Lista los usuarios del sistema. Exclusivo de admin."""
    users = get_all_users()
    clean = [{"username": u["username"], "role": u["role"]} for u in users]
    return build_response(
        "success",
        f"Usuarios registrados: {len(clean)}",
        data={"users": clean},
    )


# -----------------------------------------------------------------------------
# Handlers de comandos — camiones
# -----------------------------------------------------------------------------

def validate_truck_payload(data: dict) -> tuple[bool, dict, str]:
    """
    Valida y normaliza los campos comunes de un camion.

    Retorna (ok, payload_normalizado, mensaje_error).
    - ok=True  → payload contiene los campos limpios listos para la BD.
    - ok=False → payload es {} y mensaje_error describe el problema.

    Campos validados:
      plate_number     — obligatorio, normalizado a mayusculas
      model            — obligatorio
      capacity_kg      — entero positivo obligatorio
      status           — uno de VALID_STATUSES (default: "available")
      current_location — opcional, None si se omite
    """
    plate_number     = data.get("plate_number", "").strip()
    model            = data.get("model", "").strip()
    capacity_kg_raw  = data.get("capacity_kg")
    status           = data.get("status", "available").strip().lower()
    current_location = (data.get("current_location") or "").strip() or None

    if not plate_number:
        return False, {}, "Se requiere 'plate_number'."
    if not model:
        return False, {}, "Se requiere 'model'."
    if capacity_kg_raw is None:
        return False, {}, "Se requiere 'capacity_kg'."
    try:
        capacity_kg = int(capacity_kg_raw)
        if capacity_kg <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return False, {}, "'capacity_kg' debe ser un entero positivo."
    if status not in VALID_STATUSES:
        return False, {}, f"Estado invalido. Valores permitidos: {', '.join(VALID_STATUSES)}."

    return True, {
        "plate_number"    : plate_number.upper(),
        "model"           : model,
        "capacity_kg"     : capacity_kg,
        "status"          : status,
        "current_location": current_location,
    }, ""


def handle_list_trucks(session: dict, ip_str: str) -> dict:
    """
    Devuelve la lista completa de camiones desde MySQL.
    Registra TRUCK_LISTED en auditoria.
    """
    trucks = get_all_trucks()
    if trucks is None:
        return build_response("error", "Error al obtener la lista de camiones de la base de datos.")

    log_event(
        "TRUCK_LISTED",
        user_id    = session["user_id"],
        detail     = f"{session['username']} consulto la flota ({len(trucks)} camion(es))",
        ip_address = ip_str,
    )
    return build_response(
        "success",
        f"Flota — {len(trucks)} camion(es) registrado(s).",
        data={"trucks": trucks},
    )


def handle_truck_detail(data: dict, session: dict, ip_str: str) -> dict:
    """
    Devuelve el detalle de un camion por matricula.
    Registra TRUCK_DETAIL en auditoria si el camion existe.
    """
    plate = data.get("plate_number", "").strip()
    if not plate:
        return build_response("error", "Falta el campo 'plate_number'.")

    truck = get_truck_by_query(plate)
    if not truck:
        return build_response("error", f"Camion '{plate.upper()}' no encontrado.")

    log_event(
        "TRUCK_DETAIL",
        user_id    = session["user_id"],
        detail     = f"{session['username']} consulto camion {truck['plate_number']}",
        ip_address = ip_str,
    )
    return build_response(
        "success",
        f"Camion '{truck['plate_number']}' encontrado.",
        data={
            "plate_number"    : truck["plate_number"],
            "model"           : truck["model"],
            "capacity_kg"     : truck["capacity_kg"],
            "status"          : truck["status"],
            "current_location": truck["current_location"],
            "created_at"      : truck["created_at"],
            "updated_at"      : truck["updated_at"],
        },
    )


def handle_create_truck(data: dict, session: dict, ip_str: str) -> dict:
    """Crea un nuevo camion. Delega la validacion a validate_truck_payload."""
    ok, payload, error_msg = validate_truck_payload(data)
    if not ok:
        return build_response("error", error_msg)

    result = create_truck(
        payload["plate_number"], payload["model"],
        payload["capacity_kg"], payload["status"], payload["current_location"],
    )
    if result["success"]:
        log_event(
            "TRUCK_CREATED",
            user_id    = session["user_id"],
            detail     = f"{session['username']} creo camion {payload['plate_number']} ({payload['model']})",
            ip_address = ip_str,
        )
        return build_response("success", f"Camion '{payload['plate_number']}' creado correctamente.")
    return build_response("error", result["error"])


def handle_update_truck(data: dict, session: dict, ip_str: str) -> dict:
    """Modifica un camion existente. Delega la validacion a validate_truck_payload."""
    ok, payload, error_msg = validate_truck_payload(data)
    if not ok:
        return build_response("error", error_msg)

    result = update_truck(
        payload["plate_number"], payload["model"],
        payload["capacity_kg"], payload["status"], payload["current_location"],
    )
    if result["success"]:
        log_event(
            "TRUCK_UPDATED",
            user_id    = session["user_id"],
            detail     = f"{session['username']} actualizo camion {payload['plate_number']}",
            ip_address = ip_str,
        )
        return build_response("success", f"Camion '{payload['plate_number']}' actualizado correctamente.")
    return build_response("error", result["error"])


def handle_delete_truck(data: dict, session: dict, ip_str: str) -> dict:
    """
    Elimina un camion por matricula.
    Acepta 'plate_number' (Fase 2) o 'query' como alias de compatibilidad.
    Registra TRUCK_DELETED en auditoria.
    """
    plate = (data.get("plate_number") or data.get("query") or "").strip()
    if not plate:
        return build_response("error",
                              "Se requiere 'plate_number' con la matricula del camion.")

    result = delete_truck(plate)
    if result["success"]:
        log_event(
            "TRUCK_DELETED",
            user_id    = session["user_id"],
            detail     = f"{session['username']} elimino camion {result['plate_number']}",
            ip_address = ip_str,
        )
        return build_response(
            "success",
            f"Camion '{result['plate_number']}' eliminado correctamente.",
        )
    return build_response("error", result["error"])


# -----------------------------------------------------------------------------
# Handlers de comandos — auditoria (solo admin via RBAC)
# -----------------------------------------------------------------------------

def handle_list_audit_logs(data: dict, session: dict, ip_str: str) -> dict:
    try:
        limit = int(data.get("limit", 50))
        if not (1 <= limit <= 500):
            limit = 50
    except (ValueError, TypeError):
        limit = 50

    logs = get_audit_logs(limit)
    return build_response(
        "success",
        f"Auditoria — ultimos {len(logs)} registro(s).",
        data={"logs": logs},
    )


def handle_filter_audit_logs_by_user(data: dict, session: dict, ip_str: str) -> dict:
    username = data.get("username", "").strip()
    if not username:
        return build_response("error", "Se requiere el campo 'username'.")

    try:
        limit = int(data.get("limit", 50))
        if not (1 <= limit <= 500):
            limit = 50
    except (ValueError, TypeError):
        limit = 50

    logs = get_audit_logs_by_user(username, limit)
    return build_response(
        "success",
        f"Auditoria de '{username}' — {len(logs)} registro(s).",
        data={"logs": logs},
    )


# -----------------------------------------------------------------------------
# Enrutador principal
# -----------------------------------------------------------------------------

def process_message(message: dict, client_addr: tuple) -> tuple:
    """
    Enruta el mensaje al handler correspondiente.

    Flujo de seguridad:
      1. login → permitido siempre, sin token.
      2. Validar token → session_expired si es invalido.
      3. Verificar RBAC → ACCESS_DENIED si el rol no tiene permiso.
      4. Ejecutar handler.

    Retorna (response_dict, session_dict | None).
    """
    command = message.get("type", "").strip().lower()
    data    = message.get("data", {})
    token   = message.get("token", "").strip()
    ip_str  = f"{client_addr[0]}:{client_addr[1]}"

    if not isinstance(data, dict):
        data = {}

    logger.info(f"[{client_addr}] Comando recibido: '{command}'")

    # ── 1. login — sin token ─────────────────────────────────────────────────
    if command == "login":
        return handle_login(data, client_addr), None

    # ── 2. Validar token ─────────────────────────────────────────────────────
    session = validate_token(token)
    if session is None:
        logger.warning(f"[{client_addr}] '{command}' rechazado — token invalido.")
        return build_response(
            "error",
            "Sesion no valida. Inicia sesion de nuevo con 'login'.",
            data={"session_expired": True},
        ), None

    # ── 3. Verificar RBAC ────────────────────────────────────────────────────
    if not check_permission(session["role"], command, session["username"], ip_str):
        log_event(
            "ACCESS_DENIED",
            user_id    = session["user_id"],
            detail     = f"Comando denegado: '{command}' para rol '{session['role']}'",
            ip_address = ip_str,
        )
        return build_response(
            "error",
            f"Permiso denegado. Tu rol '{session['role']}' no puede ejecutar '{command}'.",
        ), session

    logger.info(
        f"[{client_addr}] '{session['username']}' "
        f"(rol: {session['role']}) ejecuta '{command}'"
    )

    # ── 4. Ejecutar comando autorizado ───────────────────────────────────────

    if command == "logout":
        revoke_token(token)
        logger.info(
            f"[{client_addr}] Logout de '{session['username']}'. "
            f"Sesiones activas: {active_count()}"
        )
        log_event(
            "LOGOUT",
            user_id    = session["user_id"],
            detail     = f"{session['username']} cerro sesion",
            ip_address = ip_str,
        )
        return build_response("success", "Sesion cerrada correctamente."), session

    elif command == "ping":
        return build_response("success", "pong"), session

    elif command == "help":
        all_commands = {
            "login"       : "Inicia sesion.",
            "logout"      : "Cierra sesion y revoca el token.",
            "ping"        : "Comprueba la conexion.",
            "help"        : "Muestra los comandos disponibles.",
            "list_trucks" : "Lista todos los camiones registrados.",
            "truck_detail": "Detalle de un camion por matricula.",
            "create_truck": "Crea un nuevo camion en la flota.",
            "update_truck": "Modifica un camion existente por matricula.",
            "delete_truck": "Elimina un camion de la flota por matricula.",
            "list_users"               : "[ADMIN] Lista todos los usuarios.",
            "create_user"              : "[ADMIN] Crea un nuevo usuario.",
            "delete_user"              : "[ADMIN] Elimina un usuario.",
            "list_audit_logs"          : "[ADMIN] Muestra los ultimos registros de auditoria.",
            "filter_audit_logs_by_user": "[ADMIN] Filtra la auditoria por nombre de usuario.",
            "exit"                     : "Desconecta el cliente.",
        }
        allowed = PERMISSIONS.get(session["role"], set()) | {"login", "exit"}
        visible = {k: v for k, v in all_commands.items() if k in allowed}
        return build_response(
            "success",
            f"Comandos para rol '{session['role']}':",
            data=visible,
        ), session

    # trucks — nombres Fase 2 (aliases Fase 1 en parentesis)
    elif command == "list_trucks":
        return handle_list_trucks(session, ip_str), session

    elif command in ("truck_detail", "truck_status"):
        return handle_truck_detail(data, session, ip_str), session

    elif command in ("create_truck", "add_truck"):
        return handle_create_truck(data, session, ip_str), session

    elif command == "update_truck":
        return handle_update_truck(data, session, ip_str), session

    elif command == "delete_truck":
        return handle_delete_truck(data, session, ip_str), session

    # usuarios
    elif command == "list_users":
        return handle_list_users(session), session

    elif command == "create_user":
        return handle_create_user(data, session, ip_str), session

    elif command == "delete_user":
        return handle_delete_user(data, session, ip_str), session

    elif command == "list_audit_logs":
        return handle_list_audit_logs(data, session, ip_str), session

    elif command == "filter_audit_logs_by_user":
        return handle_filter_audit_logs_by_user(data, session, ip_str), session

    else:
        return build_response(
            "error",
            f"Comando desconocido: '{command}'. Escribe 'help'.",
        ), session


# -----------------------------------------------------------------------------
# Gestion de conexiones
# -----------------------------------------------------------------------------

def _log_disconnect(addr: tuple, reason: str) -> None:
    try:
        log_event(
            "CLIENT_DISCONNECT",
            user_id    = None,
            detail     = f"Desconexion desde {addr[0]}:{addr[1]} — motivo: {reason}",
            ip_address = f"{addr[0]}:{addr[1]}",
        )
    except Exception:
        pass


def handle_client(conn: ssl.SSLSocket, addr: tuple) -> None:
    cipher_name = conn.cipher()[0] if conn.cipher() else "unknown"
    logger.info(f"[{addr}] Conexion TLS establecida. Cifrado: {conn.cipher()}")

    log_event(
        "CLIENT_CONNECT",
        user_id    = None,
        detail     = f"Nueva conexion TLS desde {addr[0]}:{addr[1]} — cifrado: {cipher_name}",
        ip_address = f"{addr[0]}:{addr[1]}",
    )

    last_token: str | None = None
    disconnect_reason      = "EOF"

    with conn:
        buffer = ""
        while True:
            try:
                chunk = conn.recv(BUFFER_SIZE).decode(ENCODING, errors="replace")
                if not chunk:
                    logger.info(f"[{addr}] Cliente desconectado (EOF).")
                    disconnect_reason = "EOF"
                    break

                buffer += chunk

                if len(buffer) > MAX_BUFFER:
                    logger.warning(f"[{addr}] Buffer supero el limite. Cerrando conexion.")
                    send_response(conn, build_response("error", "Mensaje demasiado grande."))
                    break

                while "\n" in buffer:
                    raw_msg, buffer = buffer.split("\n", 1)
                    raw_msg = raw_msg.strip()
                    if not raw_msg:
                        continue

                    try:
                        message = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        send_response(conn, build_response("error", "Formato JSON invalido."))
                        continue

                    incoming_token = message.get("token", "")
                    if incoming_token:
                        last_token = incoming_token

                    if message.get("type", "").lower() == "exit":
                        if last_token:
                            revoke_token(last_token)
                        logger.info(f"[{addr}] Cliente solicito desconexion.")
                        send_response(conn, build_response("success", "Hasta pronto!"))
                        disconnect_reason = "EXIT_LIMPIO"
                        _log_disconnect(addr, disconnect_reason)
                        return

                    response, session = process_message(message, addr)
                    send_response(conn, response)
                    logger.info(f"[{addr}] Respuesta enviada — {response['status']}")

            except ssl.SSLError as e:
                logger.warning(f"[{addr}] Error SSL: {e}")
                disconnect_reason = f"SSL_ERROR: {e}"
                break
            except (ConnectionResetError, BrokenPipeError):
                logger.warning(f"[{addr}] Conexion interrumpida abruptamente.")
                disconnect_reason = "CONEXION_INTERRUMPIDA"
                break
            except OSError as e:
                logger.warning(f"[{addr}] Error de socket: {e}")
                break
            except UnicodeDecodeError as e:
                logger.warning(f"[{addr}] Error de codificacion: {e}")
                send_response(conn, build_response("error", "Codificacion invalida. Usa UTF-8."))
            except Exception as e:
                logger.error(f"[{addr}] Error inesperado en hilo: {e}")
                try:
                    log_event(
                        "SERVER_ERROR",
                        user_id    = None,
                        detail     = f"Error inesperado en hilo {addr}: {e}",
                        ip_address = f"{addr[0]}:{addr[1]}",
                    )
                except Exception:
                    pass
                break

    if last_token:
        revoke_token(last_token)
    _log_disconnect(addr, disconnect_reason)
    logger.info(f"[{addr}] Hilo finalizado. Sesiones activas: {active_count()}")


def accept_clients(server_socket: ssl.SSLSocket, shutdown_event: threading.Event) -> None:
    logger.info(f"Servidor TLS escuchando en {HOST}:{PORT}...")
    logger.info("Esperando conexiones seguras de clientes...\n")

    while not shutdown_event.is_set():
        try:
            conn, addr = server_socket.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
            logger.info(f"Hilo lanzado para {addr}. Activos: {threading.active_count() - 1}")
        except socket.timeout:
            # Timeout normal del accept() — revisamos shutdown_event y continuamos.
            continue
        except ssl.SSLError as e:
            if not shutdown_event.is_set():
                logger.warning(f"Handshake TLS fallido: {e}")
        except OSError:
            if shutdown_event.is_set():
                break
            logger.error("Error inesperado en el socket.")
            break
        except Exception as e:
            if not shutdown_event.is_set():
                logger.error(f"Error al aceptar conexion: {e}")


# -----------------------------------------------------------------------------
# Punto de entrada
# -----------------------------------------------------------------------------

def main():
    _print_server_banner()
    logger.info("Iniciando PSP-TRUCKS Server — Fase 2")

    shutdown_event = threading.Event()
    server_socket  = None

    try:
        if not test_connection():
            logger.error("No se puede conectar a MySQL. Comprueba que XAMPP esta activo.")
            sys.exit(1)

        if not validate_trucks_schema():
            logger.error(
                "Esquema de trucks incorrecto. "
                "Ejecuta: mysql -u root psp_trucks < database/reset_trucks_phase2.sql"
            )
            sys.exit(1)

        ssl_context = create_ssl_context()
        raw_socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw_socket.settimeout(1.0)
        raw_socket.bind((HOST, PORT))
        raw_socket.listen(10)
        server_socket = ssl_context.wrap_socket(raw_socket, server_side=True)
        logger.info("Socket TLS listo.")

        accept_clients(server_socket, shutdown_event)

    except FileNotFoundError as e:
        logger.error(f"\n{e}")
    except KeyboardInterrupt:
        logger.info("\nCtrl+C detectado. Cerrando servidor...")
    finally:
        shutdown_event.set()
        if server_socket:
            try:
                server_socket.close()
            except Exception:
                pass
        logger.info("Servidor detenido correctamente.")


if __name__ == "__main__":
    main()
