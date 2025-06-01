from sqlalchemy.orm import Session
from sqlalchemy import delete, func, or_ # Добавляем func для count и or_ для поиска
from . import models, schemas
from .security import get_password_hash, verify_password
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple # Добавляем Optional и Tuple
from datetime import datetime # Для фильтрации по дате
from . import encryption
import random
import string # для генерации резервных кодов
from .security import create_refresh_token_value
from .config import settings
import uuid
from . import encryption # Наш модуль шифрования
import base64
# --- User ---
def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.user_id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Temporary 2FA/Registration Codes ---
def create_pending_registration_code(
    db: Session, 
    email: str, 
    username: str, 
    password_hash: str, 
    code: str, 
    expires_delta_minutes: int = 15 # Даем больше времени на подтверждение регистрации
) -> models.TwoFactorTempCode:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_delta_minutes)
    # Удаляем предыдущие незавершенные попытки регистрации на этот email
    db.execute(
        delete(models.TwoFactorTempCode)
        .where(models.TwoFactorTempCode.pending_email == email)
        .where(models.TwoFactorTempCode.purpose == "registration_verify")
    )
    # db.commit()

    db_code = models.TwoFactorTempCode(
        pending_email=email,
        pending_username=username,
        pending_password_hash=password_hash,
        code=code,
        purpose="registration_verify",
        expires_at=expires_at
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code

def get_valid_pending_registration_code(
    db: Session, 
    email: str, 
    code_to_verify: str
) -> Optional[models.TwoFactorTempCode]:
    now = datetime.now(timezone.utc)
    # Очистка просроченных кодов регистрации
    db.execute(
        delete(models.TwoFactorTempCode)
        .where(models.TwoFactorTempCode.purpose == "registration_verify")
        .where(models.TwoFactorTempCode.expires_at < now)
    )
    db.commit()

    return db.query(models.TwoFactorTempCode).filter(
        models.TwoFactorTempCode.pending_email == email,
        models.TwoFactorTempCode.code == code_to_verify,
        models.TwoFactorTempCode.purpose == "registration_verify",
        models.TwoFactorTempCode.expires_at >= now
    ).first()

# Обновляем create_temp_2fa_code для логина
def create_temp_login_2fa_code(db: Session, user_id: int, code: str, expires_delta_minutes: int = 5) -> models.TwoFactorTempCode:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_delta_minutes)
    # Удаляем старые логин-коды этого пользователя
    db.execute(
        delete(models.TwoFactorTempCode)
        .where(models.TwoFactorTempCode.user_id == user_id)
        .where(models.TwoFactorTempCode.purpose == "login_2fa")
    )
    # db.commit()

    db_code = models.TwoFactorTempCode(
        user_id=user_id, 
        code=code, 
        purpose="login_2fa", 
        expires_at=expires_at
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code

# Обновляем get_valid_temp_2fa_code для логина
def get_valid_temp_login_2fa_code(db: Session, user_id: int, code_to_verify: str) -> Optional[models.TwoFactorTempCode]:
    now = datetime.now(timezone.utc)
    # Очистка просроченных логин-кодов
    db.execute(
        delete(models.TwoFactorTempCode)
        .where(models.TwoFactorTempCode.purpose == "login_2fa")
        .where(models.TwoFactorTempCode.expires_at < now) # Можно добавить и user_id для оптимизации
    ) 
    db.commit()

    return db.query(models.TwoFactorTempCode).filter(
        models.TwoFactorTempCode.user_id == user_id,
        models.TwoFactorTempCode.code == code_to_verify,
        models.TwoFactorTempCode.purpose == "login_2fa",
        models.TwoFactorTempCode.expires_at >= now
    ).first()

# delete_temp_2fa_code остается таким же, он удаляет по ID
def delete_temp_code_entry(db: Session, temp_code_id: int): # Переименовал для ясности
     db_code = db.query(models.TwoFactorTempCode).filter(models.TwoFactorTempCode.id == temp_code_id).first()
     if db_code:
         db.delete(db_code)
         db.commit()

# create_user остается почти таким же, но вызывается теперь из другого места
def create_user_from_pending(db: Session, pending_username: str, pending_email: str, pending_password_hash: str) -> models.User:
    db_user = models.User(
        username=pending_username,
        email=pending_email,
        password_hash=pending_password_hash
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# --- Backup Codes ---
def _generate_backup_code_value(length: int = 10) -> str:
    # Пример: A1B2-C3D4-E5F6 (группы по 4, разделенные дефисом)
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=length))
    # Можно добавить форматирование, если нужно
    # formatted_code = '-'.join([code[i:i+4] for i in range(0, len(code), 4)])
    return code # пока простой

def create_backup_codes_for_user(db: Session, user_id: int, num_codes: int = 5) -> list[str]:
    # Удаляем старые неиспользованные коды
    db.execute(
        delete(models.UserBackupCode)
        .where(models.UserBackupCode.user_id == user_id)
        .where(models.UserBackupCode.is_used == False)
    )
    # db.commit() # Можно коммитить здесь

    plain_codes = []
    for _ in range(num_codes):
        code_value = _generate_backup_code_value()
        plain_codes.append(code_value)
        code_hash = get_password_hash(code_value) # Хешируем как пароль
        db_backup_code = models.UserBackupCode(user_id=user_id, code_hash=code_hash)
        db.add(db_backup_code)
    db.commit()
    return plain_codes

def verify_and_use_backup_code(db: Session, user_id: int, backup_code_value: str) -> bool:
    backup_codes_query = db.query(models.UserBackupCode).filter(
        models.UserBackupCode.user_id == user_id,
        models.UserBackupCode.is_used == False
    )
    
    for db_code_entry in backup_codes_query.all():
        if verify_password(backup_code_value, db_code_entry.code_hash):
            db_code_entry.is_used = True
            db_code_entry.used_at = datetime.now(timezone.utc)
            db.commit()
            return True
    return False

# --- Refresh Tokens ---
def create_db_refresh_token(
    db: Session, 
    user_id: int, 
    # expires_delta: Optional[timedelta] = None # Можно передавать, или брать из настроек
    # Пока возьмем из настроек, если они есть
    # Для примера, зададим срок жизни здесь
    expires_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS if hasattr(settings, 'REFRESH_TOKEN_EXPIRE_DAYS') else 7 
) -> models.RefreshToken:
    
    # Удаляем старые refresh токены этого пользователя перед созданием нового
    # (политика "один активный refresh token на пользователя", можно изменить)
    db.execute(
        delete(models.RefreshToken)
        .where(models.RefreshToken.user_id == user_id)
    )
    # db.commit() # Можно коммитить здесь или перед добавлением нового

    token_value = create_refresh_token_value() 
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
    
    db_refresh_token = models.RefreshToken(
        user_id=user_id,
        token=token_value,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    db.commit()
    db.refresh(db_refresh_token)
    return db_refresh_token

def get_refresh_token_by_value(db: Session, token_value: str) -> Optional[models.RefreshToken]:
    now = datetime.now(timezone.utc)
    # Очистка всех просроченных refresh токенов (можно делать периодически)
    db.execute(
        delete(models.RefreshToken)
        .where(models.RefreshToken.expires_at < now)
    )
    db.commit()

    return db.query(models.RefreshToken).filter(
        models.RefreshToken.token == token_value,
        models.RefreshToken.expires_at >= now
        # Дополнительно можно проверить models.RefreshToken.revoked_at is None, если есть такое поле
    ).first()

def delete_refresh_token(db: Session, token_id: int): # Удаление по ID токена
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.id == token_id).first()
    if db_token:
        db.delete(db_token)
        db.commit()

def delete_refresh_token_by_value(db: Session, token_value: str): # Удаление по значению токена
    db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token == token_value).first()
    if db_token:
        db.delete(db_token)
        db.commit()

# --- Files ---
def create_file_metadata(
    db: Session,
    user_id: int,
    original_filename: str,
    mime_type: str,
    file_size_bytes: int,
    storage_path: str, # Путь к ЗАШИФРОВАННОМУ файлу
    file_data_iv: bytes, # IV, использованный для шифрования данных файла
    file_data_auth_tag: bytes, # Тег аутентификации для данных файла
    file_encryption_key: bytes # Сгенерированный ключ для шифрования этого файла (DEK)
) -> models.File:
    
    # Шифруем ключ файла (DEK) с помощью KEK (из settings.SECRET_KEY)
    encrypted_dek_hex, dek_iv_hex, dek_auth_tag_hex = encryption.encrypt_file_key(file_encryption_key)

    db_file = models.File(
        user_id=user_id,
        original_filename=original_filename,
        # stored_filename_uuid генерируется по умолчанию в модели
        storage_path=storage_path,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes, # Размер зашифрованного файла может немного отличаться
        encryption_algorithm="AES-256-GCM", # Хардкодим, т.к. используем его
        encryption_iv=base64.b16encode(file_data_iv).decode(),
        encryption_auth_tag=base64.b16encode(file_data_auth_tag).decode(),
        encrypted_dek_hex=encrypted_dek_hex,
        dek_iv_hex=dek_iv_hex,
        dek_auth_tag_hex=dek_auth_tag_hex
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_files_for_user(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    search_term: Optional[str] = None,
    mime_type_filter: Optional[str] = None,
    date_from_filter: Optional[datetime] = None,
    date_to_filter: Optional[datetime] = None,
    sort_by: Optional[str] = None, # Поле для сортировки: "original_filename", "uploaded_at", "mime_type", "file_size_bytes"
    sort_order: Optional[str] = "desc" # "asc" или "desc"
) -> List[models.File]:
    query = db.query(models.File).filter(models.File.user_id == user_id, models.File.deleted_at == None)

    # Фильтрация и поиск
    if search_term:
        # Ищем по имени файла ИЛИ по MIME-типу (можно расширить)
        # Используем ilike для регистронезависимого поиска
        query = query.filter(
            or_(
                models.File.original_filename.ilike(f"%{search_term}%"),
                models.File.mime_type.ilike(f"%{search_term}%")
            )
        )
    
    if mime_type_filter:
        # Точное совпадение или частичное, если нужно (например, "image/" для всех изображений)
        # query = query.filter(models.File.mime_type == mime_type_filter) 
        query = query.filter(models.File.mime_type.ilike(f"%{mime_type_filter}%"))


    if date_from_filter:
        query = query.filter(models.File.uploaded_at >= date_from_filter)
    
    if date_to_filter:
        # Прибавляем один день, чтобы включить весь день date_to_filter
        # или используем datetime с временем 23:59:59
        # query = query.filter(models.File.uploaded_at <= (date_to_filter + timedelta(days=1)))
        query = query.filter(models.File.uploaded_at <= date_to_filter)


    # Сортировка
    if sort_by:
        column_to_sort = getattr(models.File, sort_by, None)
        if column_to_sort: # Проверяем, что такое поле существует в модели
            if sort_order == "asc":
                query = query.order_by(column_to_sort.asc())
            else: # По умолчанию desc
                query = query.order_by(column_to_sort.desc())
        else:
            # По умолчанию сортируем по дате загрузки, если sort_by некорректный
            query = query.order_by(models.File.uploaded_at.desc())
    else:
        # Сортировка по умолчанию
        query = query.order_by(models.File.uploaded_at.desc())
        
    return query.offset(skip).limit(limit).all()

def count_files_for_user(
    db: Session, 
    user_id: int,
    search_term: Optional[str] = None,         # <--- ДОБАВИТЬ
    mime_type_filter: Optional[str] = None,    # <--- ДОБАВИТЬ
    date_from_filter: Optional[datetime] = None, # <--- ДОБАВИТЬ
    date_to_filter: Optional[datetime] = None    # <--- ДОБАВИТЬ
) -> int:
    query = db.query(models.File).filter(models.File.user_id == user_id, models.File.deleted_at == None)

    # Применяем те же фильтры, что и в get_files_for_user
    if search_term:
        query = query.filter(
            or_(
                models.File.original_filename.ilike(f"%{search_term}%"),
                models.File.mime_type.ilike(f"%{search_term}%")
            )
        )
    if mime_type_filter:
        query = query.filter(models.File.mime_type.ilike(f"%{mime_type_filter}%"))
    
    if date_from_filter:
        query = query.filter(models.File.uploaded_at >= date_from_filter)
    
    if date_to_filter:
        query = query.filter(models.File.uploaded_at <= date_to_filter)
        
    count = query.count()
    return count

def get_file_by_id_and_user(db: Session, file_id: int, user_id: int) -> Optional[models.File]:
    return db.query(models.File)\
        .filter(models.File.file_id == file_id)\
        .filter(models.File.user_id == user_id)\
        .filter(models.File.deleted_at == None)\
        .first()

def soft_delete_file(db: Session, file_id: int, user_id: int) -> Optional[models.File]:
    db_file = get_file_by_id_and_user(db, file_id=file_id, user_id=user_id)
    if db_file:
        db_file.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_file)
        # Файл на диске пока не удаляем, это можно делать фоновой задачей
    return db_file