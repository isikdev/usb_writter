import os
from ..wrappers.logging import logging
from ..constants import Msg, Def_val

def does_exist(key: str, data: dict) -> bool:
    """
    Проверяет наличие ключа в данных
    
    Args:
        key: Ключ для проверки
        data: Словарь данных
        
    Returns:
        bool: True если ключ существует и не пустой, иначе False
    """
    return key in data and data[key]

def check_mode(data: dict) -> str:
    """
    Определяет режим работы на основе данных конфигурации
    
    Args:
        data: Словарь данных конфигурации
        
    Returns:
        str: Режим работы (encrypt, decrypt, encryptrar, decryptrar)
    """
    if does_exist("encrypt", data):
        if does_exist("rar", data):
            return "encryptrar"
        else:
            return "encrypt"
    elif does_exist("decrypt", data):
        if does_exist("unrar", data):
            return "decryptrar"
        else:
            return "decrypt"
    return None

def process_rar_data(rar_data: dict) -> dict:
    """
    Обрабатывает данные для создания RAR архива
    
    Args:
        rar_data: Словарь с данными для RAR
        
    Returns:
        dict: Обработанные данные для RAR
    """
    result = {}
    
    if "archive_path" in rar_data:
        result["archive_path"] = rar_data["archive_path"]
    else:
        result["archive_path"] = "archive.rar"
        
    if "piece_size" in rar_data:
        result["piece_size"] = rar_data["piece_size"]
    else:
        result["piece_size"] = "15m"
        
    if "recovery_procent" in rar_data:
        result["recovery_procent"] = rar_data["recovery_procent"]
    else:
        result["recovery_procent"] = 5
        
    return result

def process_unrar_data(unrar_data: dict) -> dict:
    """
    Обрабатывает данные для извлечения из RAR архива
    
    Args:
        unrar_data: Словарь с данными для извлечения
        
    Returns:
        dict: Обработанные данные для извлечения
    """
    result = {}
    
    if "first_archive_path" in unrar_data:
        result["first_archive_path"] = unrar_data["first_archive_path"]
    else:
        result["first_archive_path"] = "archive.rar"
        
    if "output" in unrar_data:
        result["output"] = unrar_data["output"]
    else:
        result["output"] = "."
        
    if "password" in unrar_data:
        result["password"] = unrar_data["password"]
        
    return result

def get_split_mode(data: dict) -> bool:
    """
    Определяет, включен ли режим разделения контейнера
    
    Args:
        data: Словарь данных конфигурации
        
    Returns:
        bool: True если режим разделения включен, иначе False
    """
    if "split_mode" in data:
        return data["split_mode"]
    return Def_val.split_mode

def get_min_chunk_ratio(data: dict) -> float:
    """
    Получает минимальное соотношение размера куска
    
    Args:
        data: Словарь данных конфигурации
        
    Returns:
        float: Минимальное соотношение размера куска
    """
    if "min_chunk_ratio" in data:
        return data["min_chunk_ratio"]
    return Def_val.min_chunk_ratio 