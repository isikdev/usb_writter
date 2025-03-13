import os
import random
import string
import secrets
from typing import Optional
from .logging import logging

def generate_random_container(size: int, path: str) -> bool:
    """
    Генерирует случайный контейнер при неверном пароле
    
    Args:
        size: Размер контейнера
        path: Путь для сохранения контейнера
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    try:
        with open(path, 'wb') as f:
            # Генерируем случайные данные блоками по 1 МБ
            block_size = 1024 * 1024
            remaining = size
            
            while remaining > 0:
                chunk_size = min(block_size, remaining)
                f.write(secrets.token_bytes(chunk_size))
                remaining -= chunk_size
                
        return True
    except Exception as e:
        logging.error(f"Ошибка при создании случайного контейнера: {str(e)}")
        return False

def validate_password(password: str, expected_password: str) -> bool:
    """
    Проверяет пароль без утечки информации о времени выполнения
    
    Args:
        password: Введенный пароль
        expected_password: Ожидаемый пароль
        
    Returns:
        bool: True если пароль верный, иначе False
    """
    if not password or not expected_password:
        return False
        
    # Используем secrets.compare_digest для защиты от атак по времени
    return secrets.compare_digest(password, expected_password)

def handle_invalid_password(container_size: int, output_path: str) -> None:
    """
    Обрабатывает случай неверного пароля
    
    Args:
        container_size: Размер контейнера
        output_path: Путь для сохранения невалидного контейнера
    """
    # Генерируем случайный контейнер вместо вывода ошибки
    generate_random_container(container_size, output_path)
    # Не выводим сообщение об ошибке, чтобы не дать информацию атакующему
    logging.info(f"Операция завершена, результат сохранен в {output_path}")

def secure_delete_file(file_path: str, passes: int = 3) -> bool:
    """
    Безопасно удаляет файл с перезаписью случайными данными
    
    Args:
        file_path: Путь к файлу
        passes: Количество проходов перезаписи
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    if not os.path.exists(file_path):
        return True
        
    try:
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'r+b') as f:
            for _ in range(passes):
                f.seek(0)
                f.write(secrets.token_bytes(file_size))
                f.flush()
                os.fsync(f.fileno())
                
        os.remove(file_path)
        return True
    except Exception as e:
        logging.error(f"Ошибка при безопасном удалении файла: {str(e)}")
        try:
            os.remove(file_path)
        except:
            pass
        return False 