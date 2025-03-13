import os
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from tqdm import tqdm
from crypto.wrappers.logging import logging
from crypto.constants import Msg

def encrypt_data(data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    Шифрует данные используя AES-256-CBC
    
    Args:
        data: Данные для шифрования
        key: Ключ шифрования (256 бит)
        iv: Вектор инициализации (128 бит)
        
    Returns:
        bytes: Зашифрованные данные
    """
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    encryptor = cipher.encryptor()
    
    # Добавляем PKCS7 паддинг
    block_size = 16
    padder = lambda data: data + bytes([block_size - len(data) % block_size] * (block_size - len(data) % block_size))
    padded_data = padder(data)
    
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return encrypted_data

def decrypt_data(encrypted_data: bytes, key: bytes, iv: bytes) -> bytes:
    """
    Дешифрует данные с помощью AES-256-CBC
    
    Args:
        encrypted_data: Зашифрованные данные
        key: Ключ шифрования (256 бит)
        iv: Вектор инициализации (128 бит)
        
    Returns:
        bytes: Дешифрованные данные
    """
    backend = default_backend()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
    decryptor = cipher.decryptor()
    
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Удаляем PKCS7 паддинг
    unpadder = lambda padded_data: padded_data[:-padded_data[-1]] if padded_data and padded_data[-1] <= 16 else padded_data
    decrypted_data = unpadder(decrypted_padded_data)
    
    return decrypted_data

def encrypt_file(input_file: str, output_file: str, key: bytes, iv: bytes, buffer_size: int = 1024 * 1024) -> bool:
    """
    Шифрует файл с помощью AES-256-CBC
    
    Args:
        input_file: Путь к входному файлу
        output_file: Путь к выходному файлу
        key: Ключ шифрования (256 бит)
        iv: Вектор инициализации (128 бит)
        buffer_size: Размер буфера для чтения
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    try:
        file_size = os.path.getsize(input_file)
        
        with open(input_file, 'rb') as in_file, open(output_file, 'wb') as out_file:
            with tqdm(total=100, desc=Msg.PBar.encrypting_file, unit="%", unit_scale=False) as pbar:
                position = 0
                
                while position < file_size:
                    chunk = in_file.read(buffer_size)
                    if not chunk:
                        break
                        
                    encrypted_chunk = encrypt_data(chunk, key, iv)
                    out_file.write(encrypted_chunk)
                    
                    position += len(chunk)
                    progress_pct = min(position / file_size * 100, 100)
                    pbar.update(progress_pct - pbar.n)
                    
                    # Обновляем IV для следующего блока (для режима CBC)
                    iv = encrypted_chunk[-16:]
                    
        return True
    except Exception as e:
        logging.error(f"Ошибка при шифровании файла: {e}")
        return False

def decrypt_file(input_file: str, output_file: str, key: bytes, iv: bytes, buffer_size: int = 1024 * 1024) -> bool:
    """
    Дешифрует файл с помощью AES-256-CBC
    
    Args:
        input_file: Путь к входному файлу
        output_file: Путь к выходному файлу
        key: Ключ шифрования (256 бит)
        iv: Вектор инициализации (128 бит)
        buffer_size: Размер буфера для чтения
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    try:
        file_size = os.path.getsize(input_file)
        
        with open(input_file, 'rb') as in_file, open(output_file, 'wb') as out_file:
            with tqdm(total=100, desc=Msg.PBar.decrypting_file, unit="%", unit_scale=False) as pbar:
                position = 0
                prev_encrypted_chunk = None
                
                while position < file_size:
                    chunk = in_file.read(buffer_size)
                    if not chunk:
                        break
                        
                    decrypted_chunk = decrypt_data(chunk, key, iv)
                    out_file.write(decrypted_chunk)
                    
                    position += len(chunk)
                    progress_pct = min(position / file_size * 100, 100)
                    pbar.update(progress_pct - pbar.n)
                    
                    # Сохраняем IV для следующего блока (для режима CBC)
                    iv = chunk[-16:]
                    prev_encrypted_chunk = chunk
                    
        return True
    except Exception as e:
        logging.error(f"Ошибка при дешифровании файла: {e}")
        return False

def generate_iv(size: int = 16) -> bytes:
    """
    Генерирует случайный вектор инициализации
    
    Args:
        size: Размер вектора инициализации в байтах
        
    Returns:
        bytes: Случайный вектор инициализации
    """
    return secrets.token_bytes(size) 