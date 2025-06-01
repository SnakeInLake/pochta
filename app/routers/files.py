# app/routers/files.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile, Query
from fastapi.responses import StreamingResponse # Для скачивания файлов
from sqlalchemy.orm import Session
import shutil # Для копирования потоков файлов
import os
import uuid
import base64
from io import BytesIO
from urllib.parse import quote # <--- ДОБАВИТЬ ЭТОТ ИМПОРТ
from datetime import datetime, date # Добавляем date для query параметров даты
from typing import Optional # Добавляем Optional
from .. import schemas, crud, models, encryption
from ..database import get_db
from ..deps import get_current_active_user # Зависимость для аутентификации
from ..config import settings

router = APIRouter(
    tags=["Files"],
    dependencies=[Depends(get_current_active_user)] # Все эндпоинты здесь требуют аутентификации
)

# Определяем базовый путь для хранения файлов (лучше вынести в config.py)
# Убедитесь, что эта директория существует и у приложения есть права на запись
FILES_STORAGE_PATH = os.path.join(os.getcwd(), "user_files_encrypted") 
os.makedirs(FILES_STORAGE_PATH, exist_ok=True)


@router.post("/upload", response_model=schemas.FileInfo, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = FastAPIFile(...), 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    file_encryption_key = encryption.generate_random_file_key() # Генерируем ключ для этого файла (DEK)
    
    # Генерируем уникальное имя для хранения файла на сервере
    stored_file_uuid = uuid.uuid4()
    # Путь, где будет храниться зашифрованный файл
    # Можно добавить поддиректории на основе user_id для организации
    file_location_on_disk = os.path.join(FILES_STORAGE_PATH, f"{stored_file_uuid}.enc")

    file_data_iv = None
    file_data_auth_tag = None
    actual_file_size = 0

    try:
        # Открываем временный файл для записи зашифрованных данных
        with open(file_location_on_disk, "wb") as encrypted_file_on_disk:
            # Шифруем и пишем файл по частям
            file_data_iv, file_data_auth_tag = encryption.encrypt_file_stream(
                file.file, # file.file - это файлоподобный объект UploadFile
                encrypted_file_on_disk, 
                file_encryption_key
            )
        # Получаем размер ЗАШИФРОВАННОГО файла
        actual_file_size = os.path.getsize(file_location_on_disk)

    except Exception as e:
        # Если ошибка при шифровании/записи, удаляем частично созданный файл
        if os.path.exists(file_location_on_disk):
            os.remove(file_location_on_disk)
        print(f"Ошибка при загрузке и шифровании файла: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not upload/encrypt file: {e}")
    finally:
        await file.close() # Важно закрыть файл, который пришел в UploadFile

    if file_data_iv is None or file_data_auth_tag is None:
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Encryption metadata (IV/Tag) not generated.")

    # Сохраняем метаданные в БД
    db_file = crud.create_file_metadata(
        db=db,
        user_id=current_user.user_id,
        original_filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=actual_file_size, # Сохраняем размер зашифрованного файла
        storage_path=file_location_on_disk, # Или относительный путь, если FILES_STORAGE_PATH - базовый
        file_data_iv=file_data_iv,
        file_data_auth_tag=file_data_auth_tag,
        file_encryption_key=file_encryption_key
    )
    
    return db_file


@router.get("", response_model=schemas.FileListResponse) # Путь остается тот же
def list_user_files(
    # Параметры пагинации
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"),
    # Параметры поиска и фильтрации
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search term for filename or MIME type"),
    mime_type: Optional[str] = Query(None, max_length=50, description="Filter by MIME type (e.g., 'image/jpeg', 'image', 'pdf')"),
    date_from: Optional[date] = Query(None, description="Filter by upload date from (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter by upload date to (YYYY-MM-DD)"),
    # Параметры сортировки
    sort_by: Optional[str] = Query(
        None, 
        description="Field to sort by: 'original_filename', 'uploaded_at', 'mime_type', 'file_size_bytes'",
        # Можно использовать Enum для допустимых значений, если FastAPI/Pydantic это красиво обработает
        # regex="^(original_filename|uploaded_at|mime_type|file_size_bytes)$" # Для строгой проверки
    ),
    sort_order: Optional[str] = Query(
        "desc", 
        description="Sort order: 'asc' or 'desc'",
        regex="^(asc|desc)$" # Строго 'asc' или 'desc'
    ),
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # FastAPI автоматически преобразует date из строки "YYYY-MM-DD" в объект datetime.date
    # Для сравнения с полем DateTime в БД, их нужно будет привести к datetime.datetime
    # или сравнивать на уровне даты, если это приемлемо.
    
    datetime_from = None
    if date_from:
        datetime_from = datetime.combine(date_from, datetime.min.time()) # Начало дня

    datetime_to = None
    if date_to:
        datetime_to = datetime.combine(date_to, datetime.max.time()) # Конец дня (23:59:59.999999)
        # Или datetime_to = datetime.combine(date_to + timedelta(days=1), datetime.min.time()) и использовать < 

    # Проверка допустимых значений для sort_by (лучше через Enum, но для простоты пока так)
    allowed_sort_fields = ["original_filename", "uploaded_at", "mime_type", "file_size_bytes"]
    if sort_by and sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort_by field. Allowed fields are: {', '.join(allowed_sort_fields)}"
        )

    files_list = crud.get_files_for_user(
        db, 
        user_id=current_user.user_id, 
        skip=skip, 
        limit=limit,
        search_term=search,
        mime_type_filter=mime_type,
        date_from_filter=datetime_from,
        date_to_filter=datetime_to,
        sort_by=sort_by,
        sort_order=sort_order.lower() if sort_order else "desc" # Приводим к нижнему регистру
    )
    total_files_count = crud.count_files_for_user(
        db, 
        user_id=current_user.user_id,
        search_term=search,
        mime_type_filter=mime_type,
        date_from_filter=datetime_from,
        date_to_filter=datetime_to
    )
    return {"files": files_list, "total_files": total_files_count}


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_file = crud.get_file_by_id_and_user(db, file_id=file_id, user_id=current_user.user_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied.")

    if not os.path.exists(db_file.storage_path):
        # Это серьезная проблема, метаданные есть, а файла нет
        print(f"Критическая ошибка: файл {db_file.storage_path} не найден на диске для file_id {db_file.file_id}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File data missing on server.")

    try:
        # Дешифруем ключ файла (DEK)
        file_encryption_key = encryption.decrypt_file_key(
            encrypted_file_key_hex=db_file.encrypted_dek_hex,
            iv_hex=db_file.dek_iv_hex,
            auth_tag_hex=db_file.dek_auth_tag_hex
        )
        
        # Получаем тег аутентификации для данных файла
        file_data_auth_tag = base64.b16decode(db_file.encryption_auth_tag)

    except Exception as e:
        print(f"Ошибка при дешифровании ключа файла {db_file.file_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to prepare file for download (key error).")

    async def file_streamer():
        try:
            with open(db_file.storage_path, "rb") as encrypted_file_on_disk:
                # Создаем временный поток в памяти для дешифрованных данных
                # В реальном приложении с большими файлами лучше стримить дешифрование напрямую
                # или использовать временные файлы для дешифрованных данных, если памяти мало.
                # Для РГР BytesIO может подойти для небольших/средних файлов.
                
                # Это не самый эффективный способ для больших файлов, т.к. весь файл читается в память
                # Лучше было бы создать генератор, который читает и дешифрует по частям.
                # Но для простоты пока так:
                decrypted_stream = BytesIO()
                encryption.decrypt_file_stream(
                    encrypted_file_on_disk, 
                    decrypted_stream, 
                    file_encryption_key, 
                    file_data_auth_tag
                )
                decrypted_stream.seek(0) # Перемещаем курсор в начало потока
                while True:
                    chunk = decrypted_stream.read(4096)
                    if not chunk:
                        break
                    yield chunk
        except ValueError as ve: # Ошибка от decrypt_file_stream (InvalidTag)
            print(f"Ошибка целостности при скачивании файла {db_file.file_id}: {ve}")
            # Важно не отдавать поврежденные данные. Как обработать на клиенте?
            # Можно попробовать передать ошибку в заголовке или вернуть другой статус, но StreamingResponse сложнее.
            # Простейший вариант - просто прервать поток. Клиент получит неполный файл или ошибку сети.
            # Для Swagger это может быть не очень наглядно.
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(ve)) # Не сработает внутри генератора
            # Вместо этого можно yield b"ERROR: Decryption failed due to integrity check." и закрыть.
            # Но клиент должен это обработать.
            yield b"" # Отдаем пустой остаток или специальный маркер ошибки, если клиент умеет
        except Exception as e:
            print(f"Ошибка при потоковой передаче файла {db_file.file_id}: {e}")
            yield b"" # Аналогично

    encoded_filename = quote(db_file.original_filename.encode('utf-8'))
    
    headers = {
        # Простой filename для старых браузеров (может отобразить кракозябры, если есть не-ASCII)
        'Content-Disposition': f'attachment; filename="{db_file.original_filename.encode("latin-1", "replace").decode("latin-1")}"; filename*=UTF-8\'\'{encoded_filename}'
    }
    # ------------------------
    
    return StreamingResponse(file_streamer(), media_type=db_file.mime_type, headers=headers)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file_permanently(
    file_id: int,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_file_metadata = crud.get_file_by_id_and_user(db, file_id=file_id, user_id=current_user.user_id)
    if not db_file_metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied.")

    file_path_on_disk = db_file_metadata.storage_path

    # Сначала удаляем запись из БД
    # Вместо soft_delete можно сделать crud.hard_delete_file_metadata
    # Пока используем soft_delete для примера, но для полного удаления нужно и файл удалить.
    # Для полного удаления:
    # db.delete(db_file_metadata)
    # db.commit()
    # Для soft delete:
    deleted_meta = crud.soft_delete_file(db, file_id=file_id, user_id=current_user.user_id)
    if not deleted_meta: # Если вдруг soft_delete вернул None
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found during delete.")


    # Затем удаляем файл с диска (если это не soft delete, а полное удаление)
    # Если это soft delete, то файл на диске не трогаем, его можно удалить позже фоновой задачей
    # Если мы хотим полное удаление:
    # try:
    #     if os.path.exists(file_path_on_disk):
    #         os.remove(file_path_on_disk)
    #     else:
    #         print(f"Предупреждение: Файл {file_path_on_disk} для удаления не найден на диске (file_id: {file_id}).")
    # except Exception as e:
    #     print(f"Ошибка при удалении файла {file_path_on_disk} с диска: {e}")
    #     # Запись в БД уже удалена (или помечена как удаленная).
    #     # Нужно решить, откатывать ли удаление метаданных или оставить как есть с логированием ошибки.
    #     # Для простоты, пока просто логируем.
    #     # Можно поднять HTTPException, но ответ уже будет 204, если удаление из БД прошло.
    
    return # Для 204 ответа тело не нужно