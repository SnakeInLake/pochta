# app/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import get_db
from .security import decode_access_token

# URL для получения токена (эндпоинт /login/verify-2fa или /login/verify-backup-code)
# Важно, чтобы этот URL был относительным к префиксу API, если он есть
# Если префикс /api/v1, то tokenUrl="/api/v1/auth/login/verify-2fa" (или куда идет финальный логин)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login/verify-2fa") 

async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    print(f"DEBUG: Полученный token_input в get_current_user: {token}")
    token_data = decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = crud.get_user(db, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    # Здесь можно добавить проверку, если у пользователя есть флаг is_active
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user