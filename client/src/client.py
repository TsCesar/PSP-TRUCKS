# =============================================================================
# PSP-TRUCKS — Cliente TCP + TLS de Consola
# client/src/client.py
# Fase 1 — Paso 6
#
# Mejoras de robustez:
#   - Auto-limpia sesión local si el servidor devuelve session_expired
#   - receive_response() detecta desconexión del servidor
#   - Todos los action_* manejan respuesta None (servidor caído)
#   - Validación de inputs antes de enviar
#
# UX mejorada:
#   - Menú numerado: el usuario elige opción por número
#   - Pantalla limpia entre acciones
#   - Muestra usuario y rol activo en cabecera
#   - Menú adaptado al rol (user ve menos opciones que admin)
#   - Resultado de cada acción visible hasta pulsar otra tecla
# =============================================================================

import ssl
import os
import socket
import json
import sys

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 12345
BUFFER_SIZE = 4096
ENCODING    = "utf-8"

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CERT_FILE = os.path.join(BASE_DIR, "certs", "server.crt")

session = {
    "authenticated": False,
    "username"     : None,
    "role"         : None,
    "token"        : None,
}


# -----------------------------------------------------------------------------
# Catálogo de camiones — se obtiene del servidor (MySQL) en cada acción.
# La lista local solo se usa como fallback visual si la petición falla.
# -----------------------------------------------------------------------------
def fetch_truck_list(sock) -> list:
    """Obtiene la lista de camiones desde el servidor (MySQL)."""
    send_command(sock, build_message("list_trucks"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        return response.get("data", {}).get("trucks", [])
    return []


def fetch_user_list(sock) -> list:
    """Obtiene la lista de usuarios desde el servidor (MySQL)."""
    send_command(sock, build_message("list_users"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        return response.get("data", {}).get("users", [])
    return []


def find_truck_in_list(query: str, trucks: list) -> str | None:
    """
    Busca un camión por código (T001) o ID (TRUCK-001) en la lista local.
    Retorna el truck_id o None si no se encuentra.
    """
    q = query.strip().upper()
    for t in trucks:
        if q == t.get("code", "").upper() or q == t.get("truck_id", "").upper():
            return t["truck_id"]
    return None


def print_truck_list(trucks: list) -> None:
    """Muestra el listado de camiones con código, ID y descripción."""
    if not trucks:
        print("  (No hay camiones registrados en la flota)")
        print()
        return
    print("  ┌──────┬─────────────┬──────────────────────────────────────┐")
    print("  │ Cód  │ ID          │ Descripción                          │")
    print("  ├──────┼─────────────┼──────────────────────────────────────┤")
    for t in trucks:
        code  = t.get("code", "?")[:4]
        tid   = t.get("truck_id", "?")[:11]
        desc  = t.get("description", "?")[:36]
        print(f"  │ {code:<4} │ {tid:<11} │ {desc:<36} │")
    print("  └──────┴─────────────┴──────────────────────────────────────┘")
    print()


def print_user_list(users: list) -> None:
    """Muestra el listado de usuarios con su rol."""
    if not users:
        print("  (No hay usuarios registrados)")
        print()
        return
    print("  ┌──────────────────┬─────────┐")
    print("  │ Usuario          │ Rol     │")
    print("  ├──────────────────┼─────────┤")
    for u in users:
        uname = u.get("username", "?")[:16]
        role  = u.get("role", "?")[:7]
        print(f"  │ {uname:<16} │ {role:<7} │")
    print("  └──────────────────┴─────────┘")
    print()



# -----------------------------------------------------------------------------
# Pantalla
# -----------------------------------------------------------------------------

def clear():
    """Limpia la pantalla (Windows y Unix)."""
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    """Cabecera con estado de sesión."""
    print("╔══════════════════════════════════════════════╗")
    print("║          PSP-TRUCKS — Sistema de Flota       ║")
    print("╚══════════════════════════════════════════════╝")
    if session["authenticated"]:
        print(f"  Usuario : {session['username']}")
        print(f"  Rol     : {session['role']}")
    else:
        print("  Sin sesión activa")
    print()


def pause():
    """Espera a que el usuario pulse Enter antes de volver al menú."""
    input("\n  Pulsa Enter para continuar...")


# -----------------------------------------------------------------------------
# Contexto TLS
# -----------------------------------------------------------------------------

def create_ssl_context() -> ssl.SSLContext:
    if not os.path.isfile(CERT_FILE):
        raise FileNotFoundError(f"Certificado no encontrado: {CERT_FILE}")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_verify_locations(cafile=CERT_FILE)
    context.check_hostname = False
    context.verify_mode    = ssl.CERT_REQUIRED
    return context


# -----------------------------------------------------------------------------
# Comunicación
# -----------------------------------------------------------------------------

def send_command(sock: ssl.SSLSocket, message: dict) -> None:
    raw = json.dumps(message, ensure_ascii=False) + "\n"
    sock.sendall(raw.encode(ENCODING))


def receive_response(sock: ssl.SSLSocket) -> dict | None:
    """
    Recibe y parsea la respuesta JSON del servidor.
    Retorna None si el servidor se desconecta o hay error.
    """
    try:
        buffer = ""
        while "\n" not in buffer:
            chunk = sock.recv(BUFFER_SIZE).decode(ENCODING, errors="replace")
            if not chunk:
                # El servidor cerró el socket
                return None
            buffer += chunk
        return json.loads(buffer.split("\n", 1)[0])
    except (ssl.SSLError, OSError, BrokenPipeError):
        return None
    except json.JSONDecodeError:
        return None
    except Exception:
        return None


def handle_server_response(response: dict | None) -> dict | None:
    """
    Post-procesa la respuesta del servidor.
    Si el servidor indica que la sesión expiró, limpia la sesión local.
    Retorna la respuesta sin modificar para que la función llamante la muestre.
    """
    if response is None:
        return None

    # El servidor devuelve session_expired=True cuando el token ya no es válido
    data = response.get("data", {}) or {}
    if data.get("session_expired") and session["authenticated"]:
        session["authenticated"] = False
        session["username"]      = None
        session["role"]          = None
        session["token"]         = None
        print("\n  [AVISO] Tu sesión ha expirado. Debes iniciar sesión de nuevo.")

    return response


def build_message(command_type: str, data: dict = None) -> dict:
    message = {
        "type": command_type,
        "data": data if data is not None else {},
    }
    if command_type != "login" and session["token"]:
        message["token"] = session["token"]
    return message


# -----------------------------------------------------------------------------
# Presentación de resultados
# -----------------------------------------------------------------------------

def print_result(response: dict | None) -> None:
    """Muestra el resultado de un comando de forma clara."""
    if response is None:
        print("\n  [ERROR] Sin respuesta del servidor. ¿Sigue activo?")
        return

    status    = response.get("status", "?")
    message   = response.get("message", "")
    data      = response.get("data")
    timestamp = response.get("timestamp", "")

    print()
    if status == "success":
        print(f"  ✔  {message}")
    else:
        print(f"  ✖  {message}")

    if data:
        display = {k: v for k, v in data.items() if k != "token"}
        if display:
            print()
            for key, value in display.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")

    if timestamp:
        print(f"\n  Servidor: {timestamp}")


# -----------------------------------------------------------------------------
# Acciones del menú
# -----------------------------------------------------------------------------

MAX_LOGIN_ATTEMPTS = 3

def action_login(sock: ssl.SSLSocket) -> None:
    """
    Solicita credenciales con un máximo de MAX_LOGIN_ATTEMPTS intentos.
    Si se agotan los intentos, vuelve al menú principal sin autenticar.
    """
    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        clear()
        print_header()
        print("  ── Iniciar sesión ──────────────────────────\n")
        print(f"  Intento {attempt} de {MAX_LOGIN_ATTEMPTS}\n")

        username = input("  Usuario    : ").strip()
        if not username:
            print("  [AVISO] El usuario no puede estar vacío.")
            pause()
            continue

        print("  (La contraseña viaja cifrada por TLS)")
        password = input("  Contraseña : ").strip()
        if not password:
            print("  [AVISO] La contraseña no puede estar vacía.")
            pause()
            continue

        send_command(sock, build_message("login", {"username": username, "password": password}))
        response = handle_server_response(receive_response(sock))
        print_result(response)

        if response and response.get("status") == "success":
            data = response.get("data", {})
            session["authenticated"] = True
            session["username"]      = data.get("username")
            session["role"]          = data.get("role")
            session["token"]         = data.get("token")
            print(f"\n  Bienvenido, {session['username']} ({session['role']})")
            pause()
            return

        restantes = MAX_LOGIN_ATTEMPTS - attempt
        if restantes > 0:
            print(f"\n  [AVISO] Credenciales incorrectas. Te quedan {restantes} intento(s).")
        else:
            print("\n  [AVISO] Número máximo de intentos alcanzado. Volviendo al menú.")
        pause()



def action_logout(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Cerrar sesión ───────────────────────────\n")

    send_command(sock, build_message("logout"))
    response = handle_server_response(receive_response(sock))
    print_result(response)

    if response and response.get("status") == "success":
        session["authenticated"] = False
        session["username"]      = None
        session["role"]          = None
        session["token"]         = None

    pause()


def action_ping(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Ping ────────────────────────────────────\n")
    send_command(sock, build_message("ping"))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def action_help(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Comandos disponibles ────────────────────\n")
    send_command(sock, build_message("help"))
    response = handle_server_response(receive_response(sock))

    if response and response.get("status") == "success" and response.get("data"):
        cmds = response["data"]
        # Calcular ancho de columna izquierda
        max_cmd = max(len(k) for k in cmds) if cmds else 10
        col = max(max_cmd + 2, 14)

        print(f"  ┌{'─' * col}┬{'─' * (52 - col)}┐")
        print(f"  │ {'Comando':<{col-2}} │ {'Descripción':<{52 - col - 2}} │")
        print(f"  ├{'─' * col}┼{'─' * (52 - col)}┤")
        for cmd, desc in cmds.items():
            # Truncar descripción si es muy larga
            desc_str = desc[:50 - col] if len(desc) > 50 - col else desc
            print(f"  │ {cmd:<{col-2}} │ {desc_str:<{52 - col - 2}} │")
        print(f"  └{'─' * col}┴{'─' * (52 - col)}┘")
        print()
        print(f"  Rol activo: {session['role']}")
    else:
        print_result(response)

    pause()


def action_truck_status(sock: ssl.SSLSocket) -> None:
    """
    Muestra la flota desde MySQL y permite buscar por código (T001)
    o ID completo (TRUCK-001). Bucle hasta introducir 0.

    Si el camión no está en la lista local (por ejemplo, se acaba de añadir),
    se envía la consulta directamente al servidor. Así siempre se detectan
    los camiones recién añadidos sin tener que salir y volver a entrar.
    """
    last_result = None

    while True:
        clear()
        print_header()
        print("  ── Estado de camión ────────────────────────\n")
        trucks = fetch_truck_list(sock)
        print_truck_list(trucks)

        if last_result:
            print_result(last_result)
            print()

        print("  Introduce el código (ej: T001) o el ID completo (ej: TRUCK-001).")
        query = input("  Camión [0 para salir]: ").strip()

        if query == "0" or query == "":
            return

        if not query:
            continue

        # Buscar en la lista local primero para obtener el truck_id canónico.
        # Si no está (camión recién añadido en esta sesión), usar el query
        # directamente: el servidor buscará por código o ID en MySQL.
        truck_id = find_truck_in_list(query, trucks) or query.upper()

        send_command(sock, build_message("truck_status", {"truck_id": truck_id}))
        last_result = handle_server_response(receive_response(sock))



def action_create_user(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Crear nuevo usuario [ADMIN] ─────────────\n")

    # Mostrar usuarios existentes
    users = fetch_user_list(sock)
    if users:
        print("  Usuarios actuales:")
        print_user_list(users)
        last_u = users[-1]
        print(f"  Último registrado : {last_u.get('username')} (rol: {last_u.get('role')})")
        print()

    username = input("  Nuevo usuario  : ").strip()
    if not username:
        print("  [AVISO] El usuario no puede estar vacío.")
        pause()
        return

    print("  (La contraseña viaja cifrada por TLS)")
    password = input("  Contraseña     : ").strip()
    if not password:
        print("  [AVISO] La contraseña no puede estar vacía.")
        pause()
        return

    print("  Roles disponibles: [1] user  [2] admin")
    rol_input = input("  Rol [1/2 o nombre]: ").strip().lower()
    role = {"1": "user", "2": "admin"}.get(rol_input, rol_input)
    if role not in ("user", "admin"):
        print("  [AVISO] Rol no válido. Escribe 'user', 'admin', '1' o '2'.")
        pause()
        return

    send_command(sock, build_message("create_user", {
        "username": username,
        "password": password,
        "role"    : role,
    }))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def _suggest_next_truck(trucks: list) -> tuple:
    """Sugiere el siguiente código e ID disponible basándose en los existentes."""
    if not trucks:
        return "T001", "TRUCK-001"
    codes = []
    for t in trucks:
        c = t.get("code", "")
        if c.startswith("T") and c[1:].isdigit():
            codes.append(int(c[1:]))
    next_n = max(codes) + 1 if codes else 1
    return f"T{next_n:03d}", f"TRUCK-{next_n:03d}"


def action_add_truck(sock: ssl.SSLSocket) -> None:
    """Añade un nuevo camión a la flota. Disponible para user y admin."""
    clear()
    print_header()
    print("  ── Añadir camión ───────────────────────────\n")

    trucks = fetch_truck_list(sock)
    if trucks:
        print("  Camiones actuales en la flota:")
        print_truck_list(trucks)
        last = trucks[-1]
        print(f"  Último registrado : {last.get('code')} — {last.get('truck_id')} — {last.get('description')}")
        print()

    sugg_code, sugg_id = _suggest_next_truck(trucks)
    print(f"  Siguiente sugerido: código {sugg_code} / ID {sugg_id}\n")

    code = input(f"  Código corto [{sugg_code}]: ").strip().upper() or sugg_code
    truck_id = input(f"  ID completo  [{sugg_id}]: ").strip().upper() or sugg_id

    description = input("  Descripción  (ej: Camion MAN TGX - Ruta Bilbao): ").strip()
    if not description:
        print("  [AVISO] La descripción no puede estar vacía.")
        pause()
        return

    print("  Estado (available / in_transit / maintenance) [Enter = available]: ", end="")
    status = input().strip().lower() or "available"
    if status not in ("available", "in_transit", "maintenance"):
        print("  [AVISO] Estado no válido. Opciones: available, in_transit, maintenance")
        pause()
        return

    location = input("  Ubicación (ej: León) [Enter = Sin asignar]: ").strip() or "Sin asignar"

    send_command(sock, build_message("add_truck", {
        "code": code, "truck_id": truck_id,
        "description": description, "status": status, "location": location,
    }))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def action_delete_truck(sock: ssl.SSLSocket) -> None:
    """
    Elimina un camión de la flota por código (T001) o ID (TRUCK-001).
    Muestra el listado actualizado en cada iteración.
    Disponible para user y admin.
    """
    last_result = None

    while True:
        clear()
        print_header()
        print("  ── Eliminar camión ─────────────────────────\n")
        trucks = fetch_truck_list(sock)
        print_truck_list(trucks)

        if not trucks:
            print("  No hay camiones que eliminar.")
            pause()
            return

        if last_result:
            print_result(last_result)
            print()

        print("  Introduce el código (ej: T001) o el ID completo (ej: TRUCK-001).")
        query = input("  Camión a eliminar [0 para salir]: ").strip()

        if query == "0" or query == "":
            return

        # Confirmar eliminación
        truck_id = find_truck_in_list(query, trucks)
        if truck_id is None:
            print(f"  [AVISO] '{query}' no encontrado.")
            pause()
            last_result = None
            continue

        confirm = input(f"  ¿Confirmas eliminar '{truck_id}'? (s/n): ").strip().lower()
        if confirm != "s":
            print("  Operación cancelada.")
            pause()
            last_result = None
            continue

        send_command(sock, build_message("delete_truck", {"query": query}))
        last_result = handle_server_response(receive_response(sock))


def action_delete_user(sock: ssl.SSLSocket) -> None:
    """
    Elimina un usuario del sistema. Exclusivo de admin.
    Nunca permite eliminar el usuario 'admin'.
    """
    last_result = None

    while True:
        clear()
        print_header()
        print("  ── Eliminar usuario [ADMIN] ────────────────\n")
        users = fetch_user_list(sock)
        print_user_list(users)

        if len(users) <= 1:
            print("  No hay usuarios eliminables (solo queda el administrador principal).")
            pause()
            return

        if last_result:
            print_result(last_result)
            print()

        print("  Introduce el nombre del usuario a eliminar.")
        print("  (El usuario 'admin' nunca puede eliminarse)")
        username = input("  Usuario [0 para salir]: ").strip()

        if username == "0" or username == "":
            return

        if username.lower() == "admin":
            print("  [AVISO] El usuario 'admin' es el administrador principal y no puede eliminarse.")
            pause()
            last_result = None
            continue

        confirm = input(f"  ¿Confirmas eliminar al usuario '{username}'? (s/n): ").strip().lower()
        if confirm != "s":
            print("  Operación cancelada.")
            pause()
            last_result = None
            continue

        send_command(sock, build_message("delete_user", {"username": username}))
        last_result = handle_server_response(receive_response(sock))


# -----------------------------------------------------------------------------
# Menú principal
# -----------------------------------------------------------------------------

MENU_SIN_SESION = [
    ("Iniciar sesión", action_login),
]

MENU_USER = [
    ("Ping",                action_ping),
    ("Estado de camión",    action_truck_status),
    ("Añadir camión",       action_add_truck),
    ("Eliminar camión",     action_delete_truck),
    ("Ayuda / comandos",    action_help),
    ("Cerrar sesión",       action_logout),
]

MENU_ADMIN = [
    ("Ping",                action_ping),
    ("Estado de camión",    action_truck_status),
    ("Añadir camión",       action_add_truck),
    ("Eliminar camión",     action_delete_truck),
    ("Crear usuario",       action_create_user),
    ("Eliminar usuario",    action_delete_user),
    ("Ayuda / comandos",    action_help),
    ("Cerrar sesión",       action_logout),
]


def get_menu() -> list:
    if not session["authenticated"]:
        return MENU_SIN_SESION
    return MENU_ADMIN if session["role"] == "admin" else MENU_USER


def print_menu(cipher_info: tuple) -> None:
    """Muestra cabecera + menú numerado."""
    clear()
    print_header()
    cipher_name, tls_version, _ = cipher_info
    print(f"  Canal seguro: {tls_version} — {cipher_name}\n")
    print("  ── Menú ────────────────────────────────────\n")

    menu = get_menu()
    for i, (label, _) in enumerate(menu, 1):
        print(f"  [{i}] {label}")
    print(f"  [0] Salir")
    print()


def run_client() -> None:
    """Conecta al servidor y arranca el menú interactivo."""
    clear()
    print("  Conectando con PSP-TRUCKS...\n")

    try:
        ssl_context = create_ssl_context()
        raw_socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock        = ssl_context.wrap_socket(raw_socket, server_hostname=HOST)
        sock.connect((HOST, PORT))
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except ssl.SSLCertVerificationError:
        print("[ERROR] Certificado del servidor no válido.")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"[ERROR] No se puede conectar a {HOST}:{PORT}. ¿Está el servidor activo?")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    cipher_info = sock.cipher()

    with sock:
        while True:
            try:
                print_menu(cipher_info)
                menu = get_menu()

                choice = input("  Opción: ").strip()

                if choice == "0":
                    clear()
                    print_header()
                    print("  Desconectando...\n")
                    try:
                        send_command(sock, build_message("exit"))
                        receive_response(sock)
                    except Exception:
                        pass
                    print("  ¡Hasta pronto!")
                    break

                if not choice.isdigit() or int(choice) < 1 or int(choice) > len(menu):
                    clear()
                    print_header()
                    print(f"  [AVISO] Opción '{choice}' no válida.")
                    pause()
                    continue

                _, action = menu[int(choice) - 1]
                action(sock)

            except KeyboardInterrupt:
                print("\n\n  Cerrando cliente...")
                try:
                    send_command(sock, build_message("exit"))
                except Exception:
                    pass
                break
            except (OSError, BrokenPipeError):
                clear()
                print_header()
                print("  [ERROR] Se perdió la conexión con el servidor.")
                print("  Reinicia el cliente para reconectar.")
                input("  Pulsa Enter para salir...")
                break
            except Exception as e:
                clear()
                print_header()
                print(f"  [ERROR] {e}")
                pause()


def main():
    run_client()


if __name__ == "__main__":
    main()