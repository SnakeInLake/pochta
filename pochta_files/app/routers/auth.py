# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks # Добавил BackgroundTasks
from sqlalchemy.orm import Session
from datetime import timedelta,datetime,timezone

from .. import schemas, crud, models
from ..database import get_db
from ..security import create_access_token, verify_password, get_password_hash # Добавил get_password_hash
from ..two_factor import generate_2fa_code, send_2fa_code_email
from ..config import settings

router = APIRouter(
    tags=["Authentication"],
)

# Новый эндпоинт: Инициировать регистрацию (отправить код)
@router.post("/register/initiate", status_code=status.HTTP_200_OK)
def initiate_registration(
    user_in: schemas.UserCreate, 
    background_tasks: BackgroundTasks, # для отправки email в фоне
    db: Session = Depends(get_db)
):
    if crud.get_user_by_email(db, email=user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    if crud.get_user_by_username(db, username=user_in.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    # Проверяем, нет ли уже активной попытки регистрации на этот email
    existing_pending_code = db.query(models.TwoFactorTempCode)\
        .filter(models.TwoFactorTempCode.pending_email == user_in.email)\
        .filter(models.TwoFactorTempCode.purpose == "registration_verify")\
        .filter(models.TwoFactorTempCode.expires_at > datetime.now(timezone.utc))\
        .first()
    if existing_pending_code:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="A registration attempt for this email is already in progress. Please check your email or wait for the code to expire."
        )


    password_hash = get_password_hash(user_in.password)
    verification_code = generate_2fa_code()

    try:
        crud.create_pending_registration_code(
            db, 
            email=user_in.email, 
            username=user_in.username, 
            password_hash=password_hash, 
            code=verification_code
        )
        # Отправляем email в фоновой задаче, чтобы не блокировать ответ API
        background_tasks.add_task(send_2fa_code_email, recipient_email=user_in.email, code=verification_code)
    except ValueError as ve: # Ошибка конфигурации email
        # Здесь можно решить: или не давать регистрироваться, или регистрировать, но без email-подтверждения
        # Для строгости, если почта не работает, то и подтвердить не выйдет.
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Email service configuration error: {ve}")
    except Exception as e:
        # Логируем ошибку
        print(f"Ошибка при инициации регистрации для {user_in.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to initiate registration process.")

    return {"message": f"Verification code sent to {user_in.email}. Please use it to confirm your registration."}


# Новый эндпоинт: Подтвердить регистрацию кодом
@router.post("/register/confirm", response_model=schemas.UserWithBackupCodes, status_code=status.HTTP_201_CREATED)
def confirm_registration(confirm_data: schemas.RegistrationConfirm, db: Session = Depends(get_db)):
    pending_reg_entry = crud.get_valid_pending_registration_code(
        db, 
        email=confirm_data.email, 
        code_to_verify=confirm_data.code
    )

    if not pending_reg_entry or \
       not pending_reg_entry.pending_email or \
       not pending_reg_entry.pending_username or \
       not pending_reg_entry.pending_password_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification code, or incomplete pending registration data.")

    # Проверяем еще раз на случай, если кто-то успел зарегистрироваться с таким email/username,
    # пока код был валиден (маловероятно, но возможно при большой нагрузке или долгой валидности кода)
    if crud.get_user_by_email(db, email=pending_reg_entry.pending_email):
        crud.delete_temp_code_entry(db, temp_code_id=pending_reg_entry.id) # Удаляем попытку
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email was registered after code was sent. Please try registering again.")
    if crud.get_user_by_username(db, username=pending_reg_entry.pending_username):
        crud.delete_temp_code_entry(db, temp_code_id=pending_reg_entry.id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username was taken after code was sent. Please try registering again.")

    # Создаем пользователя
    created_user = crud.create_user_from_pending(
            db,
            pending_username=pending_reg_entry.pending_username,
            pending_email=pending_reg_entry.pending_email,
            pending_password_hash=pending_reg_entry.pending_password_hash
        )
        
    crud.delete_temp_code_entry(db, temp_code_id=pending_reg_entry.id)

    backup_codes_list = crud.create_backup_codes_for_user(db, user_id=created_user.user_id)
        # Печать в лог оставляем для отладки или серверного логирования
    print(f"Резервные коды для НОВОГО пользователя {created_user.username}: {backup_codes_list}")

        # Формируем новый объект ответа
    response_data = schemas.UserWithBackupCodes(
        user_id=created_user.user_id,
        username=created_user.username,
        email=created_user.email,
        created_at=created_user.created_at, # Убедитесь, что эти поля есть в модели User
        updated_at=created_user.updated_at, # и заполняются при создании
        backup_codes=backup_codes_list
    )
    return response_data


# Эндпоинты для логина остаются похожими, но используют обновленные CRUD функции
@router.post("/login/request-2fa-code", status_code=status.HTTP_200_OK)
def login_request_2fa(
    login_data: schemas.LoginRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, username=login_data.username)
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    temp_2fa_code_value = generate_2fa_code()
    try:
        crud.create_temp_login_2fa_code(db, user_id=user.user_id, code=temp_2fa_code_value, expires_delta_minutes=5)
        background_tasks.add_task(send_2fa_code_email, recipient_email=user.email, code=temp_2fa_code_value)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Email service configuration error: {ve}")
    except Exception as e:
        print(f"Ошибка отправки/сохранения 2FA кода при логине для {user.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send or save 2FA code")
    
    return {"message": f"2FA code sent to {user.email}. Please verify to complete login."}


@router.post("/login/verify-2fa", response_model=schemas.Token)
def login_verify_2fa(verify_data: schemas.TwoFactorVerify, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=verify_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or 2FA code")

    valid_code_entry = crud.get_valid_temp_login_2fa_code(db, user_id=user.user_id, code_to_verify=verify_data.code)
    if not valid_code_entry:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired 2FA code")
    
    crud.delete_temp_code_entry(db, temp_code_id=valid_code_entry.id) # Удаляем временный 2FA код
    
    # Генерируем Access Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id},
        expires_delta=access_token_expires
    )
    
    # --- ВОТ ЗДЕСЬ МЫ СОЗДАЕМ И ПОЛУЧАЕМ db_refresh_token ---
    db_refresh_token = crud.create_db_refresh_token(db, user_id=user.user_id) 
    # ---------------------------------------------------------
    
    # Проверка, что db_refresh_token был успешно создан (на всякий случай)
    if not db_refresh_token or not db_refresh_token.token:
        # Это не должно произойти, если CRUD функция работает правильно и БД доступна
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate refresh token.")

    return {
        "access_token": access_token, 
        "refresh_token": db_refresh_token.token, # Теперь db_refresh_token определен
        "token_type": "bearer"
    }


# /login/verify-backup-code остается таким же
@router.post("/login/verify-backup-code", response_model=schemas.Token) # response_model уже подходит
def login_verify_backup_code(verify_data: schemas.BackupCodeVerify, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=verify_data.email)
    # ... (проверка пользователя и backup кода) ...
    if not user: # Добавил проверку на user
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email or backup code")
        
    if not crud.verify_and_use_backup_code(db, user_id=user.user_id, backup_code_value=verify_data.backup_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or used backup code")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id},
        expires_delta=access_token_expires
    )
    db_refresh_token = crud.create_db_refresh_token(db, user_id=user.user_id)
    
    return {
        "access_token": access_token, 
        "refresh_token": db_refresh_token.token,
        "token_type": "bearer"
    }

# Новый эндпоинт для обновления Access Token с помощью Refresh Token
@router.post("/refresh-token", response_model=schemas.Token)
def refresh_access_token(
    token_data: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    refresh_token_value = token_data.refresh_token
    db_refresh_token_entry = crud.get_refresh_token_by_value(db, token_value=refresh_token_value) # Переименовал для ясности

    if not db_refresh_token_entry:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = crud.get_user(db, user_id=db_refresh_token_entry.user_id)
    if not user:
        crud.delete_refresh_token(db, token_id=db_refresh_token_entry.id) 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with refresh token not found",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username, "user_id": user.user_id},
        expires_delta=access_token_expires
    )

    # --- Ротация Refresh Token ---
    # 1. Удаляем старый использованный refresh token
    crud.delete_refresh_token(db, token_id=db_refresh_token_entry.id) 
    # 2. Генерируем и сохраняем новый refresh token
    new_db_refresh_token = crud.create_db_refresh_token(db, user_id=user.user_id)
    # ---------------------------

    return {
        "access_token": new_access_token,
        "refresh_token": new_db_refresh_token.token, # Возвращаем НОВЫЙ refresh token
        "token_type": "bearer"
    }

# (Опционально) Эндпоинт для выхода (аннулирует refresh token)
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_user(
    # Можно потребовать Access Token для этого эндпоинта, чтобы знать, чей refresh token удалять
    # current_user: models.User = Depends(get_current_user_dependency), # Нужен get_current_user
    # или передавать refresh_token в теле для аннулирования
    token_data: schemas.RefreshTokenRequest, # Для простоты пока так
    db: Session = Depends(get_db)
):
    # Находим и удаляем refresh token из БД
    # Если есть current_user, можно удалять все его токены:
    # db.execute(delete(models.RefreshToken).where(models.RefreshToken.user_id == current_user.user_id))
    # db.commit()
    # Или удаляем конкретный переданный токен:
    crud.delete_refresh_token_by_value(db, token_value=token_data.refresh_token)
    return