# =============================================================================
# PSP-TRUCKS — Control de acceso basado en roles (RBAC)
# server/src/rbac.py
# Fase 2 — Paso 3
#
# Responsabilidad unica: definir y verificar permisos por rol.
# No contiene logica de red, BD ni autenticacion.
#
# Politica de permisos:
#   user  → ping, help, logout
#             list_trucks, truck_detail, create_truck, update_truck, delete_truck
#             aliases de compatibilidad: truck_status, add_truck
#   admin → todo lo anterior + list_users, create_user, delete_user
#             list_audit_logs, filter_audit_logs_by_user
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
        "logout",
        # trucks — Fase 2 nombres definitivos
        "list_trucks",
        "truck_detail",
        "create_truck",
        "update_truck",
        "delete_truck",
        # aliases Fase 1 (compatibilidad hacia atras)
        "truck_status",
        "add_truck",
    },
    "admin": {
        "ping",
        "help",
        "logout",
        # trucks — Fase 2 nombres definitivos
        "list_trucks",
        "truck_detail",
        "create_truck",
        "update_truck",
        "delete_truck",
        # aliases Fase 1 (compatibilidad hacia atras)
        "truck_status",
        "add_truck",
        # usuarios — exclusivo admin
        "create_user",
        "delete_user",
        "list_users",
        # auditoria — exclusivo admin
        "list_audit_logs",
        "filter_audit_logs_by_user",
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