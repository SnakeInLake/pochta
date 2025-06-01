# app/encryption.py
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding # для AES-CBC, если бы использовали
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import base64

from .config import settings # Для SECRET_KEY, который будет "мастер-ключом" для шифрования ключей файлов

# --- Функции для шифрования/дешифрования ключей файлов (ДЕКов) ---
# Это упрощенный пример. В проде нужен KMS или Vault.
# Используем SECRET_KEY приложения как KEK (Key Encryption Key)
# Для простоты используем AES-GCM и для шифрования DEK.

# Генерируем ключ из SECRET_KEY приложения (должен быть 32 байта для AES-256)
# Это очень грубое KDF, в проде нужно использовать HKDF или аналоги.
KEK_SALT = b'some_kek_salt_123' # Должен быть уникальным и храниться где-то или быть статичным
def derive_kek(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, # для AES-256
        salt=salt,
        iterations=100000, # Минимум, лучше больше
        backend=default_backend()
    )
    return kdf.derive(password.encode())

KEK = derive_kek(settings.SECRET_KEY, KEK_SALT) # Ключ для шифрования ключей файлов

def encrypt_file_key(file_key: bytes) -> tuple[str, str]: # возвращает (зашифрованный_ключ_hex, iv_hex)
    iv = os.urandom(12) # GCM рекомендует 12 байт IV
    cipher = Cipher(algorithms.AES(KEK), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(file_key) + encryptor.finalize()
    # Возвращаем зашифрованный ключ и IV в hex, и тег аутентификации
    return base64.b16encode(encrypted_data).decode(), base64.b16encode(iv).decode(), base64.b16encode(encryptor.tag).decode()

def decrypt_file_key(encrypted_file_key_hex: str, iv_hex: str, auth_tag_hex: str) -> bytes:
    iv = base64.b16decode(iv_hex)
    encrypted_data = base64.b16decode(encrypted_file_key_hex)
    auth_tag = base64.b16decode(auth_tag_hex)
    cipher = Cipher(algorithms.AES(KEK), modes.GCM(iv, auth_tag), backend=default_backend())
    decryptor = cipher.decryptor()
    return decryptor.update(encrypted_data) + decryptor.finalize()

# --- Функции для шифрования/дешифрования содержимого файлов ---
def generate_random_file_key(key_size_bytes: int = 32) -> bytes: # 32 байта для AES-256
    return os.urandom(key_size_bytes)

def encrypt_file_stream(input_stream, output_stream, file_key: bytes):
    """Шифрует данные из input_stream и пишет в output_stream, используя AES-GCM."""
    iv = os.urandom(12)  # GCM рекомендует 12 байт IV
    output_stream.write(iv) # Сначала пишем IV в выходной файл/поток

    cipher = Cipher(algorithms.AES(file_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    chunk_size = 4096  # Читаем и шифруем по частям
    while True:
        chunk = input_stream.read(chunk_size)
        if not chunk:
            break
        encrypted_chunk = encryptor.update(chunk)
        output_stream.write(encrypted_chunk)
    
    encrypted_final_chunk = encryptor.finalize()
    output_stream.write(encrypted_final_chunk)
    
    # Сохраняем тег аутентификации (важно для GCM)
    # Его нужно будет сохранить в метаданных файла в БД
    auth_tag = encryptor.tag
    return iv, auth_tag # Возвращаем IV и тег, чтобы сохранить их

def decrypt_file_stream(input_stream, output_stream, file_key: bytes, auth_tag: bytes):
    """Дешифрует данные из input_stream и пишет в output_stream, используя AES-GCM."""
    iv = input_stream.read(12) # Сначала читаем IV из входного файла/потока

    cipher = Cipher(algorithms.AES(file_key), modes.GCM(iv, auth_tag), backend=default_backend())
    decryptor = cipher.decryptor()

    chunk_size = 4096 + 16 # GCM может добавлять до 16 байт (тег) на блок, читаем с запасом
    while True:
        encrypted_chunk = input_stream.read(chunk_size)
        if not encrypted_chunk:
            break
        decrypted_chunk = decryptor.update(encrypted_chunk)
        output_stream.write(decrypted_chunk)
    
    try:
        decrypted_final_chunk = decryptor.finalize() # Проверка тега аутентификации
        output_stream.write(decrypted_final_chunk)
    except Exception as e: # InvalidTag или другая ошибка, если данные повреждены/изменены
        print(f"Ошибка дешифрования (возможно, неверный ключ или поврежденные данные): {e}")
        raise ValueError("Decryption failed: Invalid authentication tag or corrupted data.") from e