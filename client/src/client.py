# =============================================================================
# PSP-TRUCKS — Cliente TCP + TLS de Consola
# client/src/client.py
# Fase 2 — Paso 2
#
# Comandos de trucks: list_trucks, truck_detail, create_truck,
#                     update_truck, delete_truck
# Comandos de usuarios: create_user, delete_user, list_users (admin)
# Comandos base: login, logout, ping, help, exit
# =============================================================================

import ssl
import os
import socket
import json
import sys
import getpass

# -----------------------------------------------------------------------------
# Configuracion
# -----------------------------------------------------------------------------

HOST        = "127.0.0.1"
PORT        = 12345
BUFFER_SIZE = 4096
ENCODING    = "utf-8"

VALID_STATUSES = ("available", "in_transit", "maintenance", "inactive")

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CERT_FILE = os.path.join(BASE_DIR, "certs", "server.crt")

session = {
    "authenticated": False,
    "username"     : None,
    "role"         : None,
    "token"        : None,
}


# -----------------------------------------------------------------------------
# Helpers internos — obtienen datos desde el servidor
# -----------------------------------------------------------------------------

def fetch_truck_list(sock) -> list:
    send_command(sock, build_message("list_trucks"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        return response.get("data", {}).get("trucks", [])
    return []


def fetch_user_list(sock) -> list:
    send_command(sock, build_message("list_users"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        return response.get("data", {}).get("users", [])
    return []


# -----------------------------------------------------------------------------
# Pantalla y presentacion
# -----------------------------------------------------------------------------

def clear():
    os.system("cls" if os.name == "nt" else "clear")


_HEADER_W = 46


def print_header():
    W = _HEADER_W
    print(f"╔{'═' * W}╗")
    print(f"║{'PSP-TRUCKS  —  Sistema de Flota':^{W}}║")
    print(f"║{'Fase 2  —  2 DAM  —  2025-2026':^{W}}║")
    print(f"╠{'═' * W}╣")
    if session["authenticated"]:
        tag  = "ADMIN" if session["role"] == "admin" else "USER"
        line = f"  {session['username']}  [{tag}]"
        print(f"║{line:<{W}}║")
    else:
        print(f"║{'  Sin sesion activa':<{W}}║")
    print(f"╚{'═' * W}╝")
    print()


def pause():
    input("\n  Pulsa Enter para continuar...")


def read_password_with_asterisks(prompt: str) -> str:
    """Lee una contrasena mostrando asteriscos caracter a caracter (Windows/msvcrt)."""
    try:
        import msvcrt
        print(prompt, end="", flush=True)
        chars = []
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                print()
                break
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x08":
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)
            else:
                chars.append(ch)
                print("*", end="", flush=True)
        return "".join(chars).strip()
    except ImportError:
        return getpass.getpass(prompt).strip()


def print_truck_list(trucks: list) -> None:
    if not trucks:
        print("  (No hay camiones registrados en la flota)")
        print()
        return
    print("  ┌──────────────┬──────────────────────┬───────────┬─────────────┬─────────────────┐")
    print("  │ Matricula    │ Modelo               │ Cap. (kg) │ Estado      │ Ubicacion       │")
    print("  ├──────────────┼──────────────────────┼───────────┼─────────────┼─────────────────┤")
    for t in trucks:
        plate    = str(t.get("plate_number") or "")[:12]
        model    = str(t.get("model") or "")[:20]
        cap      = str(t.get("capacity_kg") or "")[:9]
        status   = str(t.get("status") or "")[:11]
        location = str(t.get("current_location") or "")[:15]
        print(f"  │ {plate:<12} │ {model:<20} │ {cap:>9} │ {status:<11} │ {location:<15} │")
    print("  └──────────────┴──────────────────────┴───────────┴─────────────┴─────────────────┘")
    print()


def print_user_list(users: list) -> None:
    if not users:
        print("  (No hay usuarios registrados)")
        print()
        return
    print("  ┌──────────────────┬─────────┐")
    print("  │ Usuario          │ Rol     │")
    print("  ├──────────────────┼─────────┤")
    for u in users:
        uname = str(u.get("username") or "")[:16]
        role  = str(u.get("role") or "")[:7]
        print(f"  │ {uname:<16} │ {role:<7} │")
    print("  └──────────────────┴─────────┘")
    print()


def print_audit_logs(logs: list) -> None:
    if not logs:
        print("  (No hay registros de auditoria)")
        print()
        return
    print("  ┌──────┬──────────────────┬──────────────────────┬────────────────────────────────────┐")
    print("  │  ID  │ Usuario          │ Evento               │ Detalle                            │")
    print("  ├──────┼──────────────────┼──────────────────────┼────────────────────────────────────┤")
    for log in logs:
        lid    = str(log.get("id", ""))[:6]
        user   = str(log.get("username") or "")[:16]
        event  = str(log.get("event_type") or "")[:20]
        detail = str(log.get("detail") or "")[:34]
        print(f"  │ {lid:<5}│ {user:<16} │ {event:<20} │ {detail:<34} │")
    print("  └──────┴──────────────────┴──────────────────────┴────────────────────────────────────┘")
    print()


def print_result(response: dict | None) -> None:
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
        skip = {"token", "session_expired", "trucks", "users", "logs"}
        display = {k: v for k, v in data.items() if k not in skip}
        if display:
            print()
            for key, value in display.items():
                if isinstance(value, (dict, list)):
                    continue
                print(f"  {key}: {value}")

    if timestamp:
        print(f"\n  Servidor: {timestamp}")


# -----------------------------------------------------------------------------
# TLS
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
# Comunicacion
# -----------------------------------------------------------------------------

def send_command(sock: ssl.SSLSocket, message: dict) -> None:
    raw = json.dumps(message, ensure_ascii=False) + "\n"
    sock.sendall(raw.encode(ENCODING))


def receive_response(sock: ssl.SSLSocket) -> dict | None:
    try:
        buffer = ""
        while "\n" not in buffer:
            chunk = sock.recv(BUFFER_SIZE).decode(ENCODING, errors="replace")
            if not chunk:
                return None
            buffer += chunk
        return json.loads(buffer.split("\n", 1)[0])
    except Exception:
        return None


def handle_server_response(response: dict | None) -> dict | None:
    if response is None:
        return None
    data = response.get("data", {}) or {}
    # Limpia la sesion local siempre que el servidor indique session_expired,
    # independientemente del estado local (cubre tokens manipulados o expirados).
    if data.get("session_expired"):
        session["authenticated"] = False
        session["username"]      = None
        session["role"]          = None
        session["token"]         = None
        print("\n  [AVISO] Tu sesion ha expirado. Inicia sesion de nuevo.")
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
# Acciones — autenticacion
# -----------------------------------------------------------------------------

MAX_LOGIN_ATTEMPTS = 3


def action_login(sock: ssl.SSLSocket) -> None:
    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        clear()
        print_header()
        print("  ── Iniciar sesion ──────────────────────────\n")
        print(f"  Intento {attempt} de {MAX_LOGIN_ATTEMPTS}\n")

        username = input("  Usuario    : ").strip()
        if not username:
            print("  [AVISO] El usuario no puede estar vacio.")
            pause()
            continue

        password = read_password_with_asterisks("  Contrasena : ")
        if not password:
            print("  [AVISO] La contrasena no puede estar vacia.")
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
            print("\n  [AVISO] Numero maximo de intentos alcanzado. Volviendo al menu.")
        pause()


def action_logout(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Cerrar sesion ───────────────────────────\n")
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
        max_cmd = max(len(k) for k in cmds) if cmds else 10
        col = max(max_cmd + 2, 14)
        print(f"  ┌{'─' * col}┬{'─' * (52 - col)}┐")
        print(f"  │ {'Comando':<{col-2}} │ {'Descripcion':<{52 - col - 2}} │")
        print(f"  ├{'─' * col}┼{'─' * (52 - col)}┤")
        for cmd, desc in cmds.items():
            desc_str = desc[:50 - col] if len(desc) > 50 - col else desc
            print(f"  │ {cmd:<{col-2}} │ {desc_str:<{52 - col - 2}} │")
        print(f"  └{'─' * col}┴{'─' * (52 - col)}┘")
        print()
        print(f"  Rol activo: {session['role']}")
    else:
        print_result(response)
    pause()


# -----------------------------------------------------------------------------
# Acciones — camiones (CRUD)
# -----------------------------------------------------------------------------

def action_list_trucks(sock: ssl.SSLSocket) -> None:
    """list_trucks — lista todos los camiones. Requiere token."""
    clear()
    print_header()
    print("  ── Lista de camiones ───────────────────────\n")
    send_command(sock, build_message("list_trucks"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        trucks = response.get("data", {}).get("trucks", [])
        print_truck_list(trucks)
        print(f"  Total: {len(trucks)} camion(es) registrado(s).")
    else:
        print_result(response)
    pause()


def action_truck_detail(sock: ssl.SSLSocket) -> None:
    """truck_detail — consulta detalle por matricula. Requiere token."""
    last_result = None

    while True:
        clear()
        print_header()
        print("  ── Detalle de camion ───────────────────────\n")
        trucks = fetch_truck_list(sock)
        print_truck_list(trucks)

        if last_result:
            print_result(last_result)
            print()

        plate = input("  Matricula del camion [0 para salir]: ").strip()
        if plate == "0" or plate == "":
            return

        send_command(sock, build_message("truck_detail", {"plate_number": plate}))
        last_result = handle_server_response(receive_response(sock))


def action_create_truck(sock: ssl.SSLSocket) -> None:
    """create_truck — crea un nuevo camion. Requiere token."""
    clear()
    print_header()
    print("  ── Crear nuevo camion ──────────────────────\n")

    plate_number = input("  Matricula   (ej: 1234-ABC)     : ").strip()
    if not plate_number:
        print("  [AVISO] La matricula no puede estar vacia.")
        pause()
        return

    model = input("  Modelo      (ej: Volvo FH16)   : ").strip()
    if not model:
        print("  [AVISO] El modelo no puede estar vacio.")
        pause()
        return

    cap_raw = input("  Capacidad   (ej: 24000) en kg  : ").strip()
    try:
        capacity_kg = int(cap_raw)
        if capacity_kg <= 0:
            raise ValueError
    except (ValueError, TypeError):
        print("  [AVISO] La capacidad debe ser un entero positivo.")
        pause()
        return

    print(f"  Opciones de estado: {', '.join(VALID_STATUSES)}")
    status = input("  Estado      [Enter = available] : ").strip().lower() or "available"
    if status not in VALID_STATUSES:
        print(f"  [AVISO] Estado no valido. Opciones: {', '.join(VALID_STATUSES)}")
        pause()
        return

    current_location = input("  Ubicacion   [Enter = sin ubicacion]: ").strip() or None

    send_command(sock, build_message("create_truck", {
        "plate_number"    : plate_number,
        "model"           : model,
        "capacity_kg"     : capacity_kg,
        "status"          : status,
        "current_location": current_location,
    }))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def action_update_truck(sock: ssl.SSLSocket) -> None:
    """update_truck — modifica un camion existente. Requiere token."""
    clear()
    print_header()
    print("  ── Modificar camion ────────────────────────\n")

    trucks = fetch_truck_list(sock)
    print_truck_list(trucks)

    plate = input("  Matricula del camion a modificar [0 para salir]: ").strip()
    if plate == "0" or plate == "":
        return

    # Obtener datos actuales para mostrar como referencia
    send_command(sock, build_message("truck_detail", {"plate_number": plate}))
    detail_resp = handle_server_response(receive_response(sock))
    if not detail_resp or detail_resp.get("status") != "success":
        print_result(detail_resp)
        pause()
        return

    current = detail_resp.get("data", {})
    print(f"\n  Camion: {current.get('plate_number')} — deja en blanco para conservar el valor actual.\n")

    model_raw = input(f"  Modelo      [{current.get('model', '')}]: ").strip()
    model = model_raw if model_raw else current.get("model")
    if not model:
        print("  [AVISO] El modelo no puede quedar vacio.")
        pause()
        return

    cap_raw = input(f"  Capacidad kg [{current.get('capacity_kg', '')}]: ").strip()
    if cap_raw:
        try:
            capacity_kg = int(cap_raw)
            if capacity_kg <= 0:
                raise ValueError
        except (ValueError, TypeError):
            print("  [AVISO] La capacidad debe ser un entero positivo.")
            pause()
            return
    else:
        capacity_kg = current.get("capacity_kg")

    print(f"  Opciones de estado: {', '.join(VALID_STATUSES)}")
    status_raw = input(f"  Estado      [{current.get('status', '')}]: ").strip().lower()
    if status_raw:
        if status_raw not in VALID_STATUSES:
            print(f"  [AVISO] Estado no valido. Opciones: {', '.join(VALID_STATUSES)}")
            pause()
            return
        status = status_raw
    else:
        status = current.get("status")

    loc_raw = input(f"  Ubicacion   [{current.get('current_location') or ''}]: ").strip()
    current_location = loc_raw if loc_raw else current.get("current_location")

    send_command(sock, build_message("update_truck", {
        "plate_number"    : plate,
        "model"           : model,
        "capacity_kg"     : capacity_kg,
        "status"          : status,
        "current_location": current_location,
    }))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def action_delete_truck(sock: ssl.SSLSocket) -> None:
    """delete_truck — elimina un camion por matricula. Requiere token."""
    last_result = None

    while True:
        clear()
        print_header()
        print("  ── Eliminar camion ─────────────────────────\n")
        trucks = fetch_truck_list(sock)
        print_truck_list(trucks)

        if not trucks:
            print("  No hay camiones que eliminar.")
            pause()
            return

        if last_result:
            print_result(last_result)
            print()

        plate = input("  Matricula del camion a eliminar [0 para salir]: ").strip()
        if plate == "0" or plate == "":
            return

        confirm = input(f"  ¿Confirmas eliminar '{plate.upper()}'? (s/n): ").strip().lower()
        if confirm != "s":
            print("  Operacion cancelada.")
            pause()
            last_result = None
            continue

        send_command(sock, build_message("delete_truck", {"plate_number": plate}))
        last_result = handle_server_response(receive_response(sock))


# -----------------------------------------------------------------------------
# Acciones — usuarios (admin)
# -----------------------------------------------------------------------------

def action_create_user(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Crear nuevo usuario [ADMIN] ─────────────\n")

    users = fetch_user_list(sock)
    if users:
        print("  Usuarios actuales:")
        print_user_list(users)

    username = input("  Nuevo usuario  : ").strip()
    if not username:
        print("  [AVISO] El usuario no puede estar vacio.")
        pause()
        return

    password = read_password_with_asterisks("  Contrasena     : ")
    if not password:
        print("  [AVISO] La contrasena no puede estar vacia.")
        pause()
        return

    print("  Roles disponibles: [1] user  [2] admin")
    rol_input = input("  Rol [1/2 o nombre]: ").strip().lower()
    role = {"1": "user", "2": "admin"}.get(rol_input, rol_input)
    if role not in ("user", "admin"):
        print("  [AVISO] Rol no valido. Escribe 'user', 'admin', '1' o '2'.")
        pause()
        return

    send_command(sock, build_message("create_user", {
        "username": username,
        "password": password,
        "role"    : role,
    }))
    print_result(handle_server_response(receive_response(sock)))
    pause()


def action_delete_user(sock: ssl.SSLSocket) -> None:
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

        print("  (El usuario 'admin' nunca puede eliminarse)")
        username = input("  Usuario a eliminar [0 para salir]: ").strip()
        if username == "0" or username == "":
            return

        if username.lower() == "admin":
            print("  [AVISO] El usuario 'admin' es el administrador principal y no puede eliminarse.")
            pause()
            last_result = None
            continue

        confirm = input(f"  ¿Confirmas eliminar '{username}'? (s/n): ").strip().lower()
        if confirm != "s":
            print("  Operacion cancelada.")
            pause()
            last_result = None
            continue

        send_command(sock, build_message("delete_user", {"username": username}))
        last_result = handle_server_response(receive_response(sock))


def action_list_users(sock: ssl.SSLSocket) -> None:
    clear()
    print_header()
    print("  ── Lista de usuarios [ADMIN] ───────────────\n")
    send_command(sock, build_message("list_users"))
    response = handle_server_response(receive_response(sock))
    if response and response.get("status") == "success":
        users = response.get("data", {}).get("users", [])
        print_user_list(users)
        print(f"  Total: {len(users)} usuario(s) registrado(s).")
    else:
        print_result(response)
    pause()


# -----------------------------------------------------------------------------
# Acciones — auditoria (admin)
# -----------------------------------------------------------------------------

def action_view_audit(sock: ssl.SSLSocket) -> None:
    while True:
        clear()
        print_header()
        print("  ── Auditoria del sistema [ADMIN] ───────────\n")
        print("  [1] Ultimos registros")
        print("  [2] Filtrar por usuario")
        print("  [0] Volver")
        print()

        choice = input("  Opcion: ").strip()

        if choice == "0" or choice == "":
            return

        if choice == "1":
            lim_raw = input("  Registros a mostrar [10-500, Enter=50]: ").strip()
            try:
                limit = int(lim_raw) if lim_raw else 50
                if not (1 <= limit <= 500):
                    limit = 50
            except ValueError:
                limit = 50
            send_command(sock, build_message("list_audit_logs", {"limit": limit}))
            response = handle_server_response(receive_response(sock))
            clear()
            print_header()
            print(f"  ── Auditoria — ultimos {limit} registros ────────\n")
            if response and response.get("status") == "success":
                logs = response.get("data", {}).get("logs", [])
                print_audit_logs(logs)
                print(f"  Total mostrado: {len(logs)} registro(s).")
            else:
                print_result(response)
            pause()

        elif choice == "2":
            username = input("  Nombre de usuario a filtrar: ").strip()
            if not username:
                continue
            lim_raw = input("  Registros a mostrar [10-500, Enter=50]: ").strip()
            try:
                limit = int(lim_raw) if lim_raw else 50
                if not (1 <= limit <= 500):
                    limit = 50
            except ValueError:
                limit = 50
            send_command(sock, build_message("filter_audit_logs_by_user", {
                "username": username,
                "limit"   : limit,
            }))
            response = handle_server_response(receive_response(sock))
            clear()
            print_header()
            print(f"  ── Auditoria de '{username}' ──────────────────\n")
            if response and response.get("status") == "success":
                logs = response.get("data", {}).get("logs", [])
                print_audit_logs(logs)
                print(f"  Total mostrado: {len(logs)} registro(s).")
            else:
                print_result(response)
            pause()


# -----------------------------------------------------------------------------
# Menu principal
# -----------------------------------------------------------------------------

MENU_SIN_SESION = [
    ("Iniciar sesion",    action_login),
]

MENU_USER = [
    ("Ping",              action_ping),
    ("Lista de camiones", action_list_trucks),
    ("Detalle de camion", action_truck_detail),
    ("Crear camion",      action_create_truck),
    ("Modificar camion",  action_update_truck),
    ("Eliminar camion",   action_delete_truck),
    ("Ayuda / comandos",  action_help),
    ("Cerrar sesion",     action_logout),
]

MENU_ADMIN = [
    ("Ping",              action_ping),
    ("Lista de camiones", action_list_trucks),
    ("Detalle de camion", action_truck_detail),
    ("Crear camion",      action_create_truck),
    ("Modificar camion",  action_update_truck),
    ("Eliminar camion",   action_delete_truck),
    ("Lista de usuarios", action_list_users),
    ("Crear usuario",     action_create_user),
    ("Eliminar usuario",  action_delete_user),
    ("Ver auditoria",     action_view_audit),
    ("Ayuda / comandos",  action_help),
    ("Cerrar sesion",     action_logout),
]


def get_menu() -> list:
    if not session["authenticated"]:
        return MENU_SIN_SESION
    return MENU_ADMIN if session["role"] == "admin" else MENU_USER


def print_menu(cipher_info: tuple) -> None:
    clear()
    print_header()
    cipher_name, tls_version, _ = cipher_info
    print(f"  Canal seguro: {tls_version} — {cipher_name}\n")
    print("  ── Menu ────────────────────────────────────\n")
    menu = get_menu()
    for i, (label, _) in enumerate(menu, 1):
        print(f"  [{i}] {label}")
    print("  [0] Salir")
    print()


# -----------------------------------------------------------------------------
# Punto de entrada
# -----------------------------------------------------------------------------

def run_client() -> None:
    clear()
    W = _HEADER_W
    print()
    print(f"  ╔{'═' * W}╗")
    print(f"  ║{'PSP-TRUCKS  —  Sistema de Flota':^{W}}║")
    print(f"  ║{'Fase 2  —  2 DAM  —  2025-2026':^{W}}║")
    print(f"  ╚{'═' * W}╝")
    print()
    print(f"  Conectando a {HOST}:{PORT}...")
    print()

    try:
        ssl_context = create_ssl_context()
        raw_socket  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock        = ssl_context.wrap_socket(raw_socket, server_hostname=HOST)
        sock.connect((HOST, PORT))
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except ssl.SSLCertVerificationError:
        print("[ERROR] Certificado del servidor no valido.")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"[ERROR] No se puede conectar a {HOST}:{PORT}. ¿Esta el servidor activo?")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    cipher_info = sock.cipher()

    with sock:
        while True:
            try:
                print_menu(cipher_info)
                menu   = get_menu()
                choice = input("  Opcion: ").strip()

                if choice == "0":
                    clear()
                    print_header()
                    print("  Desconectando...\n")
                    try:
                        send_command(sock, build_message("exit"))
                        receive_response(sock)
                    except Exception:
                        pass
                    print("  Hasta pronto!")
                    break

                if not choice.isdigit() or int(choice) < 1 or int(choice) > len(menu):
                    clear()
                    print_header()
                    print(f"  [AVISO] Opcion '{choice}' no valida.")
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
                print("  [ERROR] Se perdio la conexion con el servidor.")
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
