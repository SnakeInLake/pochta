from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UUID # Добавил UUID
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime, timezone # импортируем timezone
import uuid # Для генерации UUID
from sqlalchemy import Text


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    backup_codes = relationship("UserBackupCode", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    temp_2fa_codes = relationship("TwoFactorTempCode", back_populates="user", cascade="all, delete-orphan")


class UserBackupCode(Base):
    __tablename__ = "user_backup_codes"

    backup_code_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String(255), nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="backup_codes")


class File(Base):
    __tablename__ = "files"

    file_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    # Используем UUID для stored_filename_uuid
    stored_filename_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    storage_path = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, nullable=False) # Integer обычно достаточно, если файлы не гигантские, иначе BIGINT
    encryption_algorithm = Column(String(50), nullable=False)
    encryption_iv = Column(String(24), nullable=False) # IV для данных файла (12 байт hex = 24 символа)
    encryption_auth_tag = Column(String(32), nullable=False) # Тег для данных файла (16 байт hex = 32 символа)

    # Поля для зашифрованного ключа файла (Data Encryption Key - DEK)
    encrypted_dek_hex = Column(Text, nullable=False) # Сам зашифрованный DEK
    dek_iv_hex = Column(String(24), nullable=False) # IV для шифрования DEK
    dek_auth_tag_hex = Column(String(32), nullable=False) # Тег для шифрования DEK
    
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True) # For soft delete

    owner = relationship("User", back_populates="files")


class TwoFactorTempCode(Base): # Модель теперь будет использоваться и для регистрации
    __tablename__ = "two_factor_temp_codes"

    id = Column(Integer, primary_key=True, index=True)
    # user_id может быть NULL, если это код для новой регистрации
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=True, index=True) 
    
    # Поля для предрегистрации (если user_id is NULL)
    pending_email = Column(String(255), unique=True, index=True, nullable=True) # Email для новой регистрации
    pending_username = Column(String(50), nullable=True)
    pending_password_hash = Column(String(255), nullable=True)
    
    code = Column(String(6), nullable=False) 
    purpose = Column(String(50), nullable=False, default="login_2fa") # "login_2fa" или "registration_verify"
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="temp_2fa_codes")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(Text, unique=True, index=True, nullable=False) # Сам refresh token (может быть длинным)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # revoked_at = Column(DateTime(timezone=True), nullable=True) # Для явного отзыва токена

    user = relationship("User") # Можно добавить back_populates в User, если нужно