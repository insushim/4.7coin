"""Admin login → JWT."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ...config import settings
from ..deps import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def login(form: OAuth2PasswordRequestForm = Depends()) -> dict:
    if form.username != settings.admin_username or form.password != settings.admin_password:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    token = create_access_token(subject=form.username)
    return {"access_token": token, "token_type": "bearer"}
