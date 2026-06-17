"""Router d'authentification : émission de JWT (OAuth2 password flow).

`POST /api/v1/auth/login` accepte un formulaire `username`/`password` (standard
OAuth2) et renvoie un jeton Bearer à présenter sur les endpoints de données.
"""
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from core import security
from schemas import models

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=models.Token)
def login(form: OAuth2PasswordRequestForm = Depends()):
    if not security.authenticate(form.username, form.password):
        raise security._CREDENTIALS_ERROR
    return {"access_token": security.create_access_token(form.username), "token_type": "bearer"}
