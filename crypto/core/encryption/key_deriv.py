import secrets
import hashlib
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from crypto.wrappers.logging import logging

def generate_key(password: str, salt: bytes = None, iterations: int = 100000) -> tuple:
    """
    Генерирует ключ шифрования на основе пароля
    
    Args:
        password: Пароль
        salt: Соль (если None, то генерируется случайная соль)
        iterations: Количество итераций PBKDF2
        
    Returns:
        tuple: (ключ, соль)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
        
    # Преобразуем пароль в байты
    password_bytes = password.encode('utf-8')
    
    # Используем PBKDF2 для получения ключа
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 бит
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    
    key = kdf.derive(password_bytes)
    return key, salt

def derive_iv(password: str, iv_iterations: int = 1000, iv_size: int = 16) -> bytes:
    """
    Получает вектор инициализации на основе пароля
    
    Args:
        password: Пароль
        iv_iterations: Количество итераций PBKDF2 для IV
        iv_size: Размер вектора инициализации
        
    Returns:
        bytes: Вектор инициализации
    """
    backend = default_backend()
    salt = password.encode()
    kdf_iv = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=iv_size,
        salt=salt,
        iterations=iv_iterations,
        backend=backend
    )
    password_bytes = password.encode('utf-8')
    return kdf_iv.derive(password_bytes)

def password_to_key(password: str) -> bytes:
    """
    Преобразует пароль в ключ с помощью SHA-256
    
    Args:
        password: Пароль
        
    Returns:
        bytes: Ключ
    """
    return hashlib.sha256(password.encode('utf-8')).digest()

def generate_random_key(length: int = 32) -> bytes:
    """
    Генерирует случайный ключ
    
    Args:
        length: Длина ключа в байтах
        
    Returns:
        bytes: Случайный ключ
    """
    return secrets.token_bytes(length)

def encode_key_base64(key: bytes) -> str:
    """
    Кодирует ключ в base64
    
    Args:
        key: Ключ
        
    Returns:
        str: Ключ в формате base64
    """
    return base64.b64encode(key).decode('utf-8')

def decode_key_base64(key_base64: str) -> bytes:
    """
    Декодирует ключ из base64
    
    Args:
        key_base64: Ключ в формате base64
        
    Returns:
        bytes: Декодированный ключ
    """
    return base64.b64decode(key_base64)

def verify_password(password: str, key: bytes, salt: bytes, iterations: int = 100000) -> bool:
    """
    Проверяет правильность пароля
    
    Args:
        password: Пароль для проверки
        key: Ключ, полученный ранее
        salt: Соль, использованная при генерации ключа
        iterations: Количество итераций PBKDF2
        
    Returns:
        bool: True если пароль верный, иначе False
    """
    try:
        # Получаем ключ на основе пароля и соли
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        kdf.verify(password.encode('utf-8'), key)
        return True
    except Exception:
        return False 