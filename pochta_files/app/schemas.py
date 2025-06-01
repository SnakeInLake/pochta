from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime # Убедимся что есть
from typing import List, Optional
import uuid
import re

class UserBase(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$", # Разрешаем буквы, цифры и подчеркивание
        description="Username must be 3-50 characters long and contain only letters, numbers, and underscores."
    )
    email: EmailStr # EmailStr уже обеспечивает хорошую валидацию email

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100) # Увеличил max_length

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"[0-9]", v):
            raise ValueError('Password must contain at least one digit')
        # Опционально: проверка на спецсимволы
        # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        #     raise ValueError('Password must contain at least one special character')
        return v

class User(UserBase):
    user_id: int
    created_at: datetime # Добавим для полноты
    updated_at: datetime # Добавим для полноты

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    
class LoginRequest(BaseModel):
    username: str
    password: str

class TwoFactorVerify(BaseModel): # Для проверки 2FA кода при логине
    email: EmailStr 
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")

class RegistrationConfirm(BaseModel): # Для подтверждения регистрации
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^[0-9]{6}$")

class BackupCodeVerify(BaseModel):
    email: EmailStr 
    backup_code: str

class UserWithBackupCodes(User): # Наследуемся от User, чтобы включить все поля пользователя
    backup_codes: List[str] 

class Token(BaseModel): # Эта модель теперь будет возвращать оба токена
    access_token: str
    refresh_token: str # Добавляем refresh_token
    token_type: str = "bearer" # По умолчанию

class RefreshTokenRequest(BaseModel): # Для запроса на обновление
    refresh_token: str

class FileBase(BaseModel):
    original_filename: str = Field(..., max_length=255) # Ограничение длины имени файла
    mime_type: str
    file_size_bytes: int

class FileInfo(FileBase):
    file_id: int
    stored_filename_uuid: uuid.UUID 
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# Для ответа со списком файлов
class FileListResponse(BaseModel):
    files: List[FileInfo]
    total_files: int # Если нужна пагинация или общее количество