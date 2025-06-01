from fastapi import FastAPI, Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware # Если нужен CORS
import logging # для логгирования
import sys # для логгирования
from fastapi.encoders import jsonable_encoder # Важно для корректной сериализации
import logging # Используем стандартный logging

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from .database import engine, Base
from .routers import auth
from .config import settings # импортируем настройки
from .routers import auth, files


log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s (%(filename)s:%(lineno)d)")
logger = logging.getLogger("app") # Главный логгер приложения
logger.setLevel(logging.INFO) # Уровень по умолчанию

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Опционально: Обработчик для записи в файл
# file_handler = logging.FileHandler("app.log")
# file_handler.setFormatter(log_formatter)
# logger.addHandler(file_handler)

# Логгер для uvicorn (чтобы он тоже использовал наш формат, если хотим)
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.handlers = logger.handlers # Используем те же обработчики
uvicorn_logger.propagate = False # Не передавать сообщения вышестоящим логгерам

try:
    Base.metadata.create_all(bind=engine)
    print("Таблицы успешно созданы/проверены.")
except Exception as e:
    print(f"Ошибка при создании таблиц: {e}")


app = FastAPI(
    title="Cloud Safe Folder API",
    version="0.1.0",
    description="API for a secure cloud folder with 2FA.",
    # Мы не будем указывать openapi_url здесь, а сгенерируем его кастомно
)

# Настройка логгирования (простой пример)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


# CORS Middleware (если фронтенд будет на другом домене/порту)
origins = [
    "http://localhost",
    "http://localhost:3000", # Пример порта для React
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(files.router, prefix=f"{API_V1_PREFIX}/files", tags=["Files"]) # Новый роутер

# Обработчик ошибок валидации Pydantic
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Логируем ошибку с уровнем WARNING
    # exc.errors() может содержать несериализуемые объекты, логируем строковое представление
    # или обработанные ошибки, как мы делали для ответа
    errors_for_log = []
    for error in exc.errors():
        processed_error = error.copy()
        if 'ctx' in processed_error and isinstance(processed_error['ctx'], dict) and \
           'error' in processed_error['ctx'] and isinstance(processed_error['ctx']['error'], ValueError):
            processed_error['ctx']['error'] = str(processed_error['ctx']['error'])
        if 'input' in processed_error and isinstance(processed_error['input'], bytes):
            try:
                processed_error['input'] = processed_error['input'].decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                processed_error['input'] = repr(processed_error['input'])
        errors_for_log.append(processed_error)

    logger.warning(
        f"Validation error for {request.method} {request.url} - Client: {request.client.host} - Errors: {jsonable_encoder(errors_for_log)}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(errors_for_log)}, # Используем обработанные ошибки
    )

@app.exception_handler(HTTPException) # Добавим обработчик для стандартных HTTPException
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error(
            f"HTTP error {exc.status_code} for {request.method} {request.url} - Client: {request.client.host} - Detail: {exc.detail}",
            exc_info=True # Добавляем трейсбек для серверных ошибок
        )
    elif exc.status_code >= 400:
         logger.warning(
            f"HTTP warning {exc.status_code} for {request.method} {request.url} - Client: {request.client.host} - Detail: {exc.detail}"
        )
    # Возвращаем стандартный ответ FastAPI для HTTPException
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(Exception) # Этот должен идти последним
async def generic_exception_handler(request: Request, exc: Exception):
    # Логируем ошибку с уровнем ERROR и полным трейсбеком
    logger.error(
        f"Unhandled exception for {request.method} {request.url} - Client: {request.client.host}",
        exc_info=True # Это добавит полный трейсбек в лог
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# Подключение роутеров
API_V1_PREFIX = "/api/v1" # Определяем префикс для API
app.include_router(auth.router, prefix=f"{API_V1_PREFIX}/auth", tags=["Authentication"])


@app.get(f"{API_V1_PREFIX}/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}

# Кастомная функция для модификации OpenAPI схемы
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    # Генерируем стандартную схему
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        # Можно добавить servers, tags и т.д. если нужно
    )
    
    # Добавляем или модифицируем securitySchemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}
        
    # Добавляем схему для Bearer Token, которую Swagger UI должен понять
    # и предоставить поле для ввода
    openapi_schema["components"]["securitySchemes"]["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT" # Опционально, но хорошо для документации
    }
    
    # Теперь нужно указать, что наши защищенные эндпоинты могут использовать эту схему.
    # FastAPI обычно делает это автоматически для Depends(oauth2_scheme),
    # но мы можем попробовать добавить BearerAuth как альтернативу или основной.
    # Если у вас есть эндпоинты, защищенные oauth2_scheme, FastAPI добавит
    # security requirement для него. Мы хотим, чтобы Swagger UI предложил выбор
    # или использовал BearerAuth, если мы его предоставим.

    # Можно пройтись по путям и добавить security requirement, если это необходимо,
    # но часто Swagger UI сам подхватывает все доступные securitySchemes
    # и предлагает их в окне "Authorize".
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi # Переназначаем стандартный генератор OpenAPI

if __name__ == "__main__":
    import uvicorn
    # Для запуска: uvicorn app.main:app --reload
    # или python app/main.py если такой блок есть
    uvicorn.run(app, host="0.0.0.0", port=8000)