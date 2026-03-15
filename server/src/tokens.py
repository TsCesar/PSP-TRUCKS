# =============================================================================
# PSP-TRUCKS — Gestor de tokens de sesión
# server/src/tokens.py
# Fase 1 — Paso 4
#
# Responsabilidad única: ciclo de vida de los tokens en memoria.
#   generate_token()  → crea un token y lo asocia al usuario
#   validate_token()  → devuelve los datos del usuario si el token es válido
#   revoke_token()    → elimina el token (logout o desconexión)
#
# El almacén es un dict protegido con threading.Lock — seguro con multihilo.
# No persiste en base de datos: si el servidor se reinicia, los tokens
# desaparecen y los clientes deben volver a hacer login.
# =============================================================================

import secrets
import threading
import logging
from datetime import datetime

logger = logging.getLogger("PSP-TRUCKS-Tokens")

# -----------------------------------------------------------------------------
# Almacén en memoria
#
# Estructura:
# {
#   "<token_hex>": {
#       "user_id"   : int,
#       "username"  : str,
#       "role"      : str,
#       "created_at": datetime
#   },
#   ...
# }
# -----------------------------------------------------------------------------
_store: dict       = {}
_lock: threading.Lock = threading.Lock()

# Longitud del token en bytes → 32 bytes = 64 caracteres hexadecimales
TOKEN_BYTES = 32


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------

def generate_token(user_id: int, username: str, role: str) -> str:
    """
    Genera un token criptográficamente seguro y lo registra en el almacén.

    secrets.token_hex() usa la fuente de aleatoriedad del sistema operativo —
    es imposible predecir el valor sin haberlo visto antes.

    Retorna el token como cadena de 64 caracteres hexadecimales.
    """
    token = secrets.token_hex(TOKEN_BYTES)

    with _lock:
        _store[token] = {
            "user_id"   : user_id,
            "username"  : username,
            "role"      : role,
            "created_at": datetime.now(),
        }

    logger.info(f"Token generado para '{username}' (rol: {role}) — {token[:8]}...")
    return token


def validate_token(token: str) -> dict | None:
    """
    Valida un token recibido del cliente.

    Retorna el dict de sesión {user_id, username, role, created_at}
    si el token existe, o None si no existe o está vacío.
    """
    if not token:
        return None

    with _lock:
        return _store.get(token)   # None si no existe


def revoke_token(token: str) -> bool:
    """
    Elimina un token del almacén, invalidando la sesión.

    Se llama en logout explícito y también si el cliente se desconecta
    sin hacer logout.

    Retorna True si el token existía y fue eliminado, False si no existía.
    """
    with _lock:
        if token in _store:
            username = _store[token].get("username", "?")
            del _store[token]
            logger.info(f"Token revocado para '{username}' — {token[:8]}...")
            return True
    return False


def active_count() -> int:
    """Número de sesiones activas en este momento."""
    with _lock:
        return len(_store)