# =============================================================================
# PSP-TRUCKS — Servidor TCP + TLS + Auth + Tokens + RBAC
# server/src/server.py
# Fase 1 — Paso 8
#
# Auditoría completa — eventos registrados en audit_logs:
#   LOGIN_OK / LOGIN_FAIL → auth.py
#   COMMAND               → handle_client() tras cada comando exitoso
#   ACCESS_DENIED         → process_message() al denegar por RBAC
#   USER_CREATED          → handle_create_user()
#   LOGOUT                → process_message() al ejecutar logout
#   SERVER_ERROR          → handle_client() en errores inesperados
#   CLIENT_CONNECT        → handle_client() al establecer TLS       ← NUEVO
#   CLIENT_DISCONNECT     → handle_client() al cerrar conexión      ← NUEVO
#
#   - send_response() tolerante a BrokenPipe y errores de socket
#   - Buffer con límite máximo para evitar desbordamiento
#   - data={} forzado si el cliente envía un campo 'data' inválido
#   - Respuesta especial SESSION_INVALID para que el cliente limpie su sesión
#   - Logs más detallados en desconexiones inesperadas
#   - Manejo explícito de BrokenPipeError y OSError en handle_client
#
# Módulos:
#   server.py   → sockets, TLS, protocolo, enrutado
#   rbac.py     → tabla de permisos y verificación
#   auth.py     → bcrypt + generate_token + hash_password
#   tokens.py   → almacén en memoria
#   database.py → MySQL
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
from database import (test_connection, log_event, create_user,
                       get_all_trucks, get_truck_by_query, create_truck, delete_truck,
                       get_all_users, delete_user)
from tokens   import validate_token, revoke_token, active_count
from rbac     import check_permission

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 12345
BUFFER_SIZE = 4096
ENCODING    = "utf-8"

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
# Contexto TLS
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
# Respuestas
# -----------------------------------------------------------------------------

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
    Serializa y envía la respuesta JSON al cliente.
    Retorna True si el envío fue exitoso, False si el socket está cerrado.
    """
    try:
        raw = json.dumps(response, ensure_ascii=False) + "\n"
        conn.sendall(raw.encode(ENCODING))
        return True
    except (BrokenPipeError, OSError):
        # Cliente cerró el socket antes de recibir la respuesta — no es un error crítico
        return False
    except Exception as e:
        logger.error(f"Error al enviar respuesta: {e}")
        return False


# -----------------------------------------------------------------------------
# Handlers de comandos
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
            f"[{client_addr}] Sesión iniciada — "
            f"'{username}' (rol: {auth_result['role']}) "
            f"token: {auth_result['token'][:8]}..."
        )
        return build_response(
            "success",
            "Autenticación correcta. Bienvenido a PSP-TRUCKS.",
            data={
                "username": auth_result["username"],
                "role"    : auth_result["role"],
                "token"   : auth_result["token"],
            }
        )
    return build_response("error", "Credenciales incorrectas.")


def handle_create_user(data: dict, session: dict, ip_str: str) -> dict:
    """
    Crea un nuevo usuario — exclusivo del rol admin.
    La contraseña se hashea con bcrypt antes de almacenarse.
    """
    new_username = data.get("username", "").strip()
    new_password = data.get("password", "")
    new_role     = data.get("role", "user").strip().lower()

    if not new_username or not new_password:
        return build_response("error", "Se requieren 'username' y 'password'.")

    if new_role not in ("user", "admin"):
        return build_response("error", "El rol debe ser 'user' o 'admin'.")

    # Hashear contraseña — NUNCA se almacena en texto plano
    password_hash = hash_password(new_password)

    result = create_user(new_username, password_hash, new_role)

    if result["success"]:
        log_event(
            "USER_CREATED",
            user_id    = session["user_id"],
            detail     = f"Admin '{session['username']}' creó usuario '{new_username}' (rol: {new_role})",
            ip_address = ip_str,
        )
        return build_response(
            "success",
            f"Usuario '{new_username}' creado correctamente con rol '{new_role}'.",
        )
    else:
        return build_response("error", result["error"])




def handle_add_truck(data: dict, session: dict, ip_str: str) -> dict:
    """
    Añade un nuevo camión a la flota.
    Disponible para user y admin.
    """
    code        = data.get("code", "").strip().upper()
    truck_id    = data.get("truck_id", "").strip().upper()
    description = data.get("description", "").strip()
    status      = data.get("status", "available").strip().lower()
    location    = data.get("location", "Sin asignar").strip()

    if not code or not truck_id or not description:
        return build_response("error", "Se requieren 'code', 'truck_id' y 'description'.")

    if status not in ("available", "in_transit", "maintenance"):
        return build_response("error", "El estado debe ser: available, in_transit o maintenance.")

    result = create_truck(code, truck_id, description, status, location)
    if result["success"]:
        log_event("TRUCK_CREATED", user_id=session["user_id"],
                  detail=f"{session['username']} añadió camión {truck_id} (código {code})",
                  ip_address=ip_str)
        return build_response("success", f"Camión '{truck_id}' añadido correctamente.")
    return build_response("error", result["error"])


def handle_delete_truck(data: dict, session: dict, ip_str: str) -> dict:
    """
    Elimina un camión de la flota por código (T001) o ID completo (TRUCK-001).
    Disponible para user y admin.
    """
    query = data.get("query", "").strip()
    if not query:
        return build_response("error", "Se requiere el campo 'query' con el código o ID del camión.")

    result = delete_truck(query)
    if result["success"]:
        log_event("TRUCK_DELETED", user_id=session["user_id"],
                  detail=f"{session['username']} eliminó camión {result['truck_id']}",
                  ip_address=ip_str)
        return build_response("success", f"Camión '{result['truck_id']}' eliminado correctamente.")
    return build_response("error", result["error"])


def handle_delete_user(data: dict, session: dict, ip_str: str) -> dict:
    """
    Elimina un usuario del sistema.
    Exclusivo de admin. Nunca elimina el usuario 'admin'.
    """
    username = data.get("username", "").strip()
    if not username:
        return build_response("error", "Se requiere el campo 'username'.")

    # Evitar que el admin se elimine a sí mismo
    if username.lower() == session["username"].lower():
        return build_response("error", "No puedes eliminar tu propio usuario.")

    result = delete_user(username)
    if result["success"]:
        log_event("USER_DELETED", user_id=session["user_id"],
                  detail=f"Admin '{session['username']}' eliminó usuario '{username}'",
                  ip_address=ip_str)
        return build_response("success", f"Usuario '{username}' eliminado correctamente.")
    return build_response("error", result["error"])


def handle_list_trucks(session: dict) -> dict:
    """Devuelve la lista completa de camiones de la flota desde MySQL."""
    trucks = get_all_trucks()
    if trucks is None:
        return build_response("error", "Error al obtener la lista de camiones.")
    return build_response("success", f"Flota — {len(trucks)} camión(es) registrado(s).",
                          data={"trucks": trucks})


def handle_list_users(session: dict) -> dict:
    """Devuelve la lista de usuarios del sistema. Exclusivo de admin."""
    users = get_all_users()
    # Ocultar el campo created_at completo para simplificar
    clean = [{"username": u["username"], "role": u["role"]} for u in users]
    return build_response("success", f"Usuarios registrados: {len(clean)}",
                          data={"users": clean})


# -----------------------------------------------------------------------------
# Enrutador principal
# -----------------------------------------------------------------------------

def process_message(message: dict, client_addr: tuple) -> tuple:
    """
    Enruta el mensaje al handler correspondiente.

    Flujo de seguridad:
      1. login → siempre permitido, sin token.
      2. Resto → validar token.
      3. Resto → verificar permisos RBAC.
      4. Ejecutar comando.

    Retorna (response_dict, session_data_o_None).
    """
    command  = message.get("type", "").strip().lower()
    data     = message.get("data", {})
    token    = message.get("token", "").strip()
    ip_str   = f"{client_addr[0]}:{client_addr[1]}"

    # Garantizar que 'data' siempre es un dict, aunque el cliente envíe otro tipo
    if not isinstance(data, dict):
        data = {}

    logger.info(f"[{client_addr}] Comando recibido: '{command}'")

    # ── 1. login ─────────────────────────────────────────────────────────────
    if command == "login":
        return handle_login(data, client_addr), None

    # ── 2. Validar token ─────────────────────────────────────────────────────
    session = validate_token(token)
    if session is None:
        logger.warning(f"[{client_addr}] '{command}' rechazado — token inválido.")
        return build_response(
            "error",
            "Sesión no válida. Inicia sesión de nuevo con 'login'.",
            data={"session_expired": True}   # el cliente usará esto para limpiar su sesión local
        ), None

    # ── 3. Verificar permisos RBAC ───────────────────────────────────────────
    if not check_permission(session["role"], command,
                            session["username"], ip_str):
        log_event(
            "ACCESS_DENIED",
            user_id    = session["user_id"],
            detail     = f"Comando denegado: '{command}' para rol '{session['role']}'",
            ip_address = ip_str,
        )
        return build_response(
            "error",
            f"Permiso denegado. Tu rol '{session['role']}' "
            f"no puede ejecutar '{command}'."
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
            detail     = f"{session['username']} cerró sesión",
            ip_address = ip_str,
        )
        return build_response("success", "Sesión cerrada correctamente."), session

    elif command == "ping":
        return build_response("success", "pong"), session

    elif command == "help":
        # Mostrar solo los comandos que el rol puede ejecutar
        all_commands = {
            "login"       : "Inicia sesión.",
            "logout"      : "Cierra sesión y revoca el token.",
            "ping"        : "Comprueba la conexión.",
            "help"        : "Muestra los comandos disponibles.",
            "truck_status": "Consulta el estado de un camión.",
            "add_truck"   : "Añade un camión a la flota.",
            "delete_truck": "Elimina un camión de la flota.",
            "create_user" : "[ADMIN] Crea un nuevo usuario.",
            "delete_user" : "[ADMIN] Elimina un usuario (nunca elimina 'admin').",
            "exit"        : "Desconecta el cliente.",
        }
        from rbac import PERMISSIONS
        allowed = PERMISSIONS.get(session["role"], set()) | {"login", "exit"}
        visible = {k: v for k, v in all_commands.items() if k in allowed}
        return build_response("success", f"Comandos para rol '{session['role']}':",
                              data=visible), session

    elif command == "truck_status":
        truck_id = data.get("truck_id")
        if not truck_id:
            return build_response("error", "Falta el campo 'truck_id'."), session

        simulated = {
            "TRUCK-001": {"status": "available",   "location": "León"},
            "TRUCK-002": {"status": "in_transit",  "location": "Madrid"},
            "TRUCK-003": {"status": "maintenance", "location": "Taller Central"},
        }
        if truck_id in simulated:
            return build_response(
                "success",
                f"Estado de '{truck_id}' consultado correctamente.",
                data={"truck_id": truck_id, **simulated[truck_id]},
            ), session
        return build_response("error", f"Camión '{truck_id}' no encontrado."), session

    elif command == "create_user":
        return handle_create_user(data, session, ip_str), session

    elif command == "add_truck":
        return handle_add_truck(data, session, ip_str), session

    elif command == "delete_truck":
        return handle_delete_truck(data, session, ip_str), session

    elif command == "delete_user":
        return handle_delete_user(data, session, ip_str), session

    elif command == "list_trucks":
        return handle_list_trucks(session), session

    elif command == "list_users":
        return handle_list_users(session), session

    else:
        return build_response(
            "error", f"Comando desconocido: '{command}'. Escribe 'help'."
        ), session


# -----------------------------------------------------------------------------
# Gestión de conexiones
# -----------------------------------------------------------------------------

MAX_BUFFER = BUFFER_SIZE * 16   # 64 KB — protección contra buffers desbordados

def _log_disconnect(addr: tuple, reason: str, token: str | None) -> None:
    """
    Registra la desconexión de un cliente en audit_logs.
    Se llama siempre que handle_client termina, sea limpio o abrupto.
    Falla en silencio para no interrumpir el flujo.
    """
    try:
        log_event(
            "CLIENT_DISCONNECT",
            user_id    = None,
            detail     = f"Desconexión desde {addr[0]}:{addr[1]} — motivo: {reason}",
            ip_address = f"{addr[0]}:{addr[1]}",
        )
    except Exception:
        pass


def handle_client(conn: ssl.SSLSocket, addr: tuple) -> None:
    cipher_name = conn.cipher()[0] if conn.cipher() else "unknown"
    logger.info(f"[{addr}] Conexión TLS establecida. Cifrado: {conn.cipher()}")

    # Registrar conexión entrante en auditoría
    log_event(
        "CLIENT_CONNECT",
        user_id    = None,   # aún no autenticado
        detail     = f"Nueva conexión TLS desde {addr[0]}:{addr[1]} — cifrado: {cipher_name}",
        ip_address = f"{addr[0]}:{addr[1]}",
    )

    last_token: str | None = None
    disconnect_reason = "EOF"   # se actualiza según cómo termine la conexión

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

                # Protección contra buffers excesivamente grandes
                if len(buffer) > MAX_BUFFER:
                    logger.warning(f"[{addr}] Buffer superó el límite. Cerrando conexión.")
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
                        send_response(conn, build_response("error", "Formato JSON inválido."))
                        continue

                    incoming_token = message.get("token", "")
                    if incoming_token:
                        last_token = incoming_token

                    if message.get("type", "").lower() == "exit":
                        if last_token:
                            revoke_token(last_token)
                        logger.info(f"[{addr}] Cliente solicitó desconexión.")
                        send_response(conn, build_response("success", "¡Hasta pronto!"))
                        disconnect_reason = "EXIT_LIMPIO"
                        # Registrar desconexión limpia en auditoría
                        _log_disconnect(addr, disconnect_reason, last_token)
                        return

                    response, session = process_message(message, addr)
                    send_response(conn, response)

                    if session and response.get("status") == "success":
                        log_event(
                            "COMMAND",
                            user_id    = session["user_id"],
                            detail     = f"{session['username']} ejecutó {message.get('type', '?')}",
                            ip_address = f"{addr[0]}:{addr[1]}",
                        )

                    logger.info(f"[{addr}] Respuesta enviada — {response['status']}")

            except ssl.SSLError as e:
                logger.warning(f"[{addr}] Error SSL: {e}")
                disconnect_reason = f"SSL_ERROR: {e}"
                break
            except (ConnectionResetError, BrokenPipeError):
                logger.warning(f"[{addr}] Conexión interrumpida abruptamente.")
                disconnect_reason = "CONEXION_INTERRUMPIDA"
                break
            except OSError as e:
                logger.warning(f"[{addr}] Error de socket (OSError): {e}")
                break
            except UnicodeDecodeError as e:
                logger.warning(f"[{addr}] Error de codificación: {e}")
                send_response(conn, build_response("error", "Codificación inválida. Usa UTF-8."))
            except Exception as e:
                logger.error(f"[{addr}] Error inesperado en hilo: {e}")
                # Registrar error inesperado del servidor en auditoría
                try:
                    log_event(
                        "SERVER_ERROR",
                        user_id    = None,
                        detail     = f"Error inesperado en hilo {addr}: {e}",
                        ip_address = f"{addr[0]}:{addr[1]}",
                    )
                except Exception:
                    pass   # la auditoría nunca debe interrumpir el flujo
                break

    if last_token:
        revoke_token(last_token)
    _log_disconnect(addr, disconnect_reason, last_token)
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
                logger.error(f"Error al aceptar conexión: {e}")


# -----------------------------------------------------------------------------
# Punto de entrada
# -----------------------------------------------------------------------------

def main():
    logger.info("=== PSP-TRUCKS Server — Fase 1 — Completo ===")
    logger.info("Presiona Ctrl+C para detener el servidor.")

    shutdown_event = threading.Event()
    server_socket  = None

    try:
        if not test_connection():
            logger.error("No se puede conectar a MySQL.")
            sys.exit(1)

        ssl_context = create_ssl_context()
        raw_socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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