#!/usr/bin/env python3
# =============================================================================
# PSP-TRUCKS — Generador de hashes bcrypt
# tools/generate_hashes.py
# Fase 1 — Paso 3
#
# Uso:
#   python tools/generate_hashes.py
#
# Requisitos:
#   pip install bcrypt
# =============================================================================

import bcrypt
import sys

# Usuarios a generar — modifica esta lista si necesitas otros
USERS_TO_GENERATE = [
    {"username": "conductor1", "password": "user1234",  "role": "user"},
    {"username": "admin",      "password": "admin1234", "role": "admin"},
]

BCRYPT_ROUNDS = 12   # Coste estándar recomendado (mayor = más seguro y más lento)


def generate_hash(password: str) -> str:
    """
    Genera un hash bcrypt con salt aleatorio incorporado.
    Dos llamadas con la misma contraseña producen hashes distintos,
    pero ambos válidos para bcrypt.checkpw().
    Formato: $2b$12$<22 chars salt><31 chars hash>
    """
    salt   = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_hash(password: str, hash_str: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hash_str.encode("utf-8"))


def main():
    print("=" * 70)
    print("  PSP-TRUCKS — Generador de hashes bcrypt")
    print(f"  Coste: {BCRYPT_ROUNDS} rondas")
    print("=" * 70)
    print()

    generated = []

    for user in USERS_TO_GENERATE:
        print(f"Generando hash para '{user['username']}' (rol: {user['role']})...")
        hash_str = generate_hash(user["password"])

        if not verify_hash(user["password"], hash_str):
            print(f"  [ERROR] El hash de '{user['username']}' no se verifica.")
            sys.exit(1)

        print(f"  Hash        : {hash_str}")
        print(f"  Verificación: OK")
        print()
        generated.append({**user, "password_hash": hash_str})

    # SQL listo para copiar en database/seed.sql
    print("=" * 70)
    print("  Copia este bloque en database/seed.sql")
    print("  (reemplaza el INSERT INTO users existente)")
    print("=" * 70)
    print()
    print("INSERT INTO users (username, password_hash, role_id) VALUES")

    lines = []
    for u in generated:
        lines.append(
            f"    (\n"
            f"        '{u['username']}',\n"
            f"        '{u['password_hash']}',\n"
            f"        (SELECT id FROM roles WHERE name = '{u['role']}')\n"
            f"    )"
        )
    print(",\n".join(lines))
    print("ON DUPLICATE KEY UPDATE")
    print("    password_hash = VALUES(password_hash),")
    print("    role_id       = VALUES(role_id);")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()