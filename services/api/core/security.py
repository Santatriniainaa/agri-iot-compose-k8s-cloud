"""Authentification JWT (OAuth2 password flow) — posture démo.

Un unique utilisateur de démonstration est paramétré par variables d'environnement
(`API_AUTH_USER` / `API_AUTH_PASSWORD`). Le mot de passe est comparé via un hash
bcrypt calculé au démarrage (jamais stocké en clair ailleurs que dans l'env).

Le durcissement production (annuaire d'utilisateurs, rotation des clés, refresh
tokens, TLS) reste en feuille de route — cf. ADR 0001.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from core import config

# Schéma OAuth2 : le token s'obtient via POST /api/v1/auth/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Hash du mot de passe démo calculé une fois au chargement du module.
_password_hash = _pwd.hash(config.AUTH_PASSWORD)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Identifiants invalides",
    headers={"WWW-Authenticate": "Bearer"},
)


def authenticate(username: str, password: str) -> bool:
    """Vérifie le couple identifiant / mot de passe contre l'utilisateur démo."""
    if username != config.AUTH_USER:
        return False
    return _pwd.verify(password, _password_hash)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Dépendance FastAPI : valide le JWT et renvoie le sujet (username)."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise _CREDENTIALS_ERROR
        return username
    except JWTError:
        raise _CREDENTIALS_ERROR
