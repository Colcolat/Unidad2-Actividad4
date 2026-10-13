import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

load_dotenv()

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret"
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError(
            "La contraseña debe tener al menos 8 caracteres."
        )

    return password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str
) -> bool:
    return password_hasher.verify(
        password,
        password_hash
    )


def create_access_token(user_id: int) -> str:
    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        subject = payload.get("sub")

        if subject is None:
            raise ValueError(
                "Token inválido."
            )

        return int(subject)

    except (
        InvalidTokenError,
        ValueError,
        TypeError
    ) as exc:
        raise ValueError(
            "Token inválido o expirado."
        ) from exc
