# =============================================================================
# PSP-TRUCKS — Módulo de Autenticación
# server/src/auth.py
# Fase 1 — Paso 5
#
# Añadido respecto al Paso 4:
#   - hash_password() → hashea una contraseña nueva para create_user
# =============================================================================

import bcrypt
import logging
from database import get_user_by_username, log_event
from tokens   import generate_token

logger = logging.getLogger("PSP-TRUCKS-Auth")

BCRYPT_ROUNDS = 12


# -----------------------------------------------------------------------------
# Utilidades bcrypt
# -----------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """
    Genera un hash bcrypt para una contraseña nueva.
    Usado por el comando create_user en server.py.
    La contraseña en texto plano se descarta inmediatamente tras hashear.
    """
    salt   = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verifica contraseña contra hash bcrypt. Tiempo constante.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            stored_hash.encode("utf-8")
        )
    except Exception as e:
        logger.error(f"Error en bcrypt.checkpw: {e}")
        return False


# -----------------------------------------------------------------------------
# Resultado de autenticación
# -----------------------------------------------------------------------------

def make_auth_result(success: bool, user_id: int = None,
                     username: str = None, role: str = None,
                     token: str = None, error: str = None) -> dict:
    return {
        "success" : success,
        "user_id" : user_id,
        "username": username,
        "role"    : role,
        "token"   : token,
        "error"   : error,
    }


# -----------------------------------------------------------------------------
# Autenticación
# -----------------------------------------------------------------------------

def authenticate(username: str, password: str, ip_address: str = None) -> dict:
    """
    Autentica un usuario con MySQL + bcrypt y genera token de sesión.
    """
    if not username or not password:
        logger.warning(f"[{ip_address}] Login con campos vacíos.")
        return make_auth_result(success=False, error="campos vacíos")

    user = get_user_by_username(username)

    if user is None:
        logger.warning(f"[{ip_address}] Login fallido — '{username}' no encontrado.")
        log_event("LOGIN_FAIL", user_id=None,
                  detail=f"Usuario no encontrado: {username}",
                  ip_address=ip_address)
        return make_auth_result(success=False, error="usuario no encontrado")

    if not verify_password(password, user["password_hash"]):
        logger.warning(f"[{ip_address}] Login fallido — contraseña incorrecta para '{username}'.")
        log_event("LOGIN_FAIL", user_id=user["id"],
                  detail="Contraseña incorrecta",
                  ip_address=ip_address)
        return make_auth_result(success=False, error="contraseña incorrecta")

    token = generate_token(
        user_id  = user["id"],
        username = user["username"],
        role     = user["role"],
    )

    logger.info(f"[{ip_address}] Login exitoso — '{username}' (rol: {user['role']}).")
    log_event("LOGIN_OK", user_id=user["id"],
              detail=f"Login correcto. Rol: {user['role']}",
              ip_address=ip_address)

    return make_auth_result(
        success  = True,
        user_id  = user["id"],
        username = user["username"],
        role     = user["role"],
        token    = token,
    )