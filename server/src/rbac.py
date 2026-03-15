# =============================================================================
# PSP-TRUCKS — Control de acceso basado en roles (RBAC)
# server/src/rbac.py
# Fase 1 — Paso 5
#
# Responsabilidad única: definir y verificar permisos por rol.
# No contiene lógica de red, BD ni autenticación.
#
# Política de permisos:
#   user  → ping, help, truck_status, logout
#   admin → todo lo anterior + create_user
# =============================================================================

import logging

logger = logging.getLogger("PSP-TRUCKS-RBAC")

# -----------------------------------------------------------------------------
# Tabla de permisos
# Cada rol tiene un conjunto de comandos permitidos.
# -----------------------------------------------------------------------------
PERMISSIONS: dict[str, set] = {
    "user": {
        "ping",
        "help",
        "truck_status",
        "logout",
        "add_truck",        # Cualquier usuario autenticado puede gestionar camiones
        "delete_truck",
        "list_trucks",      # Uso interno del cliente para mostrar la flota
    },
    "admin": {
        "ping",
        "help",
        "truck_status",
        "logout",
        "add_truck",
        "delete_truck",
        "create_user",      # Exclusivo de admin
        "delete_user",      # Exclusivo de admin (nunca elimina 'admin')
        "list_trucks",
        "list_users",       # Solo admin puede listar usuarios
    },
}


def is_allowed(role: str, command: str) -> bool:
    """
    Comprueba si el rol tiene permiso para ejecutar el comando.

    Retorna True si está permitido, False si no.
    Si el rol no existe en la tabla, se deniega por defecto.
    """
    allowed_commands = PERMISSIONS.get(role, set())
    return command in allowed_commands


def check_permission(role: str, command: str,
                     username: str, ip_address: str) -> bool:
    """
    Verifica el permiso y loguea el resultado.

    Retorna True si permitido, False si denegado.
    El servidor debe registrar la denegación en audit_logs.
    """
    if is_allowed(role, command):
        return True

    logger.warning(
        f"ACCESO DENEGADO — usuario: '{username}' (rol: '{role}') "
        f"intentó ejecutar '{command}' desde {ip_address}"
    )
    return False