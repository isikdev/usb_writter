import os
import glob
import psutil
import sys
import re
import hashlib
import secrets
from crypto.core.archiving import rar, zip
from crypto.core.container.splitter import ContainerSplitter
from crypto.core.par2 import creator as par2creator
from crypto.config import loader
from crypto.wrappers.logging import logging
from crypto.constants import Msg, Def_val
from crypto.modules.par2disk.par2disk import Par2Disk

def get_file_path(file_path: str) -> str:
    """
    Получает путь к директории файла
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        str: Путь к директории файла
    """
    directory = os.path.dirname(file_path)
    if not directory:
        return "."
    return directory

def encrypt_with_split_protocol(data, core) -> None:
    """
    Протокол шифрования с разделением контейнера
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("encrypt", data):
        return

    par2_data = None
    if loader.does_exist("par2", data):
        par2_data = data["par2"]

    if loader.does_exist("unrar", data):
        logging.info(Msg.Info.extracting_cont_from_rar)
        if rar.unrar_container(data["unrar"], par2_data):
            logging.info(Msg.Info.extracted_cont_from_rar)

    logging.info(Msg.Info.starting_encrypting_files)

    encrypt_config = data["encrypt"]
    core.encrypt_container(encrypt_config)

    # Получаем параметры для разделения контейнера
    piece_size = parse_size(data.get("piece_size", "15m"))
    min_chunk_ratio = loader.get_min_chunk_ratio(data)
    
    # Генерируем seed на основе хеша контейнера
    seed = generate_seed(core.container_path)
    
    # Создаем сплиттер и разделяем контейнер
    splitter = ContainerSplitter(seed=seed, min_chunk_ratio=min_chunk_ratio)
    chunks = splitter.split_container(core.container_path, piece_size)
    
    # Создаем PAR2 файлы для кусков контейнера
    if par2_data is not None and chunks:
        par2file_path = par2_data["par2file_path"]
        clean_old_par2(par2file_path)
        recovery_procent = par2_data["recovery_procent"]
        chunks_dir = os.path.dirname(chunks[0])
        par2creator.make_par2(chunks_dir, par2file_path, recovery_procent)

def encrypt_protocol(data, core) -> None:
    """
    Стандартный протокол шифрования
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("encrypt", data):
        return

    logging.info(Msg.Info.starting_encrypting_files)
    encrypt_config = data["encrypt"]

    # Создаем PAR2 файлы для контейнера до шифрования
    if loader.does_exist("par2", data):
        par2_data = data["par2"]
        par2file_path = core.container_path + ".par2"
        clean_old_par2(par2file_path)
        recovery_procent = par2_data["recovery_procent"]
        par2creator.make_par2(f"{core.container_path}/",
                       core.container_path, recovery_procent)

    core.encrypt_container(encrypt_config)

def encrypt_with_rar_protocol(data, core) -> None:
    """
    Протокол шифрования с созданием RAR архива
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("encrypt", data):
        return

    par2_data = None
    if loader.does_exist("par2", data):
        par2_data = data["par2"]

    if loader.does_exist("unrar", data):
        logging.info(Msg.Info.extracting_cont_from_rar)
        if rar.unrar_container(data["unrar"], par2_data):
            logging.info(Msg.Info.extracted_cont_from_rar)

    logging.info(Msg.Info.starting_encrypting_files)

    encrypt_config = data["encrypt"]
    core.encrypt_container(encrypt_config)

    if par2_data is not None:
        par2file_path = par2_data["par2file_path"]
        clean_old_par2(par2file_path)

    if loader.does_exist("rar", data):
        logging.info(Msg.Info.archiving_container)
        rar.rar_container(data["rar"], par2_data, core.container_path)
        if "clean" in data["rar"] and data["rar"]["clean"]:
            logging.info(Msg.Info.removing_container(core.container_path))
            os.remove(core.container_path)

def decrypt_with_rar_protocol(data, core) -> None:
    """
    Протокол дешифрования с извлечением из RAR архива
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("decrypt", data):
        return

    par2_data = None
    if loader.does_exist("par2", data):
        par2_data = data["par2"]

    if loader.does_exist("unrar", data):
        logging.info(Msg.Info.extracting_cont_from_rar)
        if rar.unrar_container(data["unrar"], par2_data):
            logging.info(Msg.Info.extracted_cont_from_rar)

    password = data["decrypt"]["password"]
    output_path = data["decrypt"]["output"]
    logging.info(Msg.Info.starting_decrypting_files)
    core.decrypt_container(output_path, data["decrypt"], password)

    if loader.does_exist("unrar", data):
        if "clean" in data["unrar"] and data["unrar"]["clean"]:
            logging.info(Msg.Info.removing_container(core.container_path))
            os.remove(core.container_path)

def decrypt_protocol(data, core) -> None:
    """
    Стандартный протокол дешифрования
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("decrypt", data):
        return

    par2file_path = core.container_path + ".par2"
    if (os.path.exists(par2file_path)):
        if not par2creator.verify_files(par2file_path):
            return

    password = data["decrypt"]["password"]
    output_path = data["decrypt"]["output"]

    logging.info(Msg.Info.starting_decrypting_files)
    core.decrypt_container(output_path, data["decrypt"], password)

def drive_encrypt_protocol(data, core) -> None:
    """
    Протокол шифрования диска
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("encrypt", data):
        return

    if Def_val.noize:
        handle = winDiskHandler.DiskHandler(
            core.container_path, core.buffer_size)
        size = handle.get_disk_size()
        handle.close_disk()

        winDiskHandler.DiskHandler.penetrateMSFSprotection(core.container_path)

        if size is None:
            logging.error(Msg.Err.cant_get_disk_size)
            raise
        if size % core.buffer_size != 0:
            logging.error(Msg.Err.disk_size_not_dividing_by_buffer(
                size, core.buffer_size))
            raise
        core.create_noise()

    par2disk_conf = None
    if loader.does_exist("par2disk", data):
        par2disk_conf = data["par2disk"]
    par2disk = Par2Disk(
        par2disk_conf, core.container_path, core.buffer_size)

    if not Def_val.noize:
        par2disk.verify_and_repair_disk()

    logging.info(Msg.Info.starting_encrypting_files)
    encrypt_config = data["encrypt"]

    core.encrypt_container(encrypt_config)

    par2disk.create_disk_parity()

def drive_decrypt_protocol(data, core) -> None:
    """
    Протокол дешифрования диска
    
    Args:
        data: Данные конфигурации
        core: Объект ядра
    """
    if not loader.does_exist("decrypt", data):
        return

    par2disk_conf = None
    if loader.does_exist("par2disk", data):
        par2disk_conf = data["par2disk"]
    par2disk = Par2Disk(
        par2disk_conf, core.container_path, core.buffer_size)

    par2disk.verify_and_repair_disk()

    password = data["decrypt"]["password"]
    output_path = data["decrypt"]["output"]

    logging.info(Msg.Info.starting_decrypting_files)
    core.decrypt_container(output_path, data["decrypt"], password)

def isContainerDisk(core) -> bool:
    """
    Проверяет, является ли контейнер диском
    
    Args:
        core: Объект ядра
        
    Returns:
        bool: True если контейнер является диском, иначе False
    """
    def isLinuxDev():
        if "/dev/" in core.container_path:
            logging.error(Msg.Err.linux_drive_not_supported)
            raise

    def isWindowsDev():
        if re.fullmatch(r"[A-Za-z]:", core.container_path):
            core.change_container_path(rf"\\.\{core.container_path}")
            return True
        else:
            return False

    return isLinuxDev() or isWindowsDev()

def clean_old_par2(par2file_path: str) -> None:
    """
    Удаляет старые PAR2 файлы
    
    Args:
        par2file_path: Базовый путь к PAR2 файлам
    """
    par2creator.clean_old_par2(par2file_path)

def generate_seed(file_path: str) -> str:
    """
    Генерирует seed на основе хеша файла
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        str: Сгенерированный seed
    """
    if not os.path.exists(file_path):
        return secrets.token_hex(8)
        
    try:
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Читаем только начало и конец файла для ускорения
            f.seek(0)
            hasher.update(f.read(1024 * 1024))  # Первый мегабайт
            
            f.seek(max(0, os.path.getsize(file_path) - 1024 * 1024))
            hasher.update(f.read(1024 * 1024))  # Последний мегабайт
            
        return hasher.hexdigest()[:16]
    except Exception as e:
        logging.error(f"Ошибка при генерации seed: {str(e)}")
        return secrets.token_hex(8)

def parse_size(size_str: str) -> int:
    """
    Преобразует строковое представление размера в байты
    
    Args:
        size_str: Строковое представление размера (например, "10M")
        
    Returns:
        int: Размер в байтах
    """
    units = {
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024,
        't': 1024 * 1024 * 1024 * 1024,
    }
    
    size_str = size_str.lower()
    if size_str[-1] in units:
        return int(float(size_str[:-1]) * units[size_str[-1]])
    else:
        try:
            return int(size_str)
        except ValueError:
            logging.error(Msg.Err.invalid_size_string_format)
            return 0

def pipeline(data):
    """
    Основной конвейер обработки
    
    Args:
        data: Данные конфигурации
    """
    from crypto.core import Core
    
    core = Core(data)

    if isContainerDisk(core):
        mode = loader.check_mode(data)
        if mode is not None:
            core.set_disk_mode(True)
            if "encrypt" in mode:
                drive_encrypt_protocol(data, core)
            elif "decrypt" in mode:
                drive_decrypt_protocol(data, core)
        return

    if os.path.exists(core.container_path):
        container_size = os.path.getsize(core.container_path)

    mode = loader.check_mode(data)
    split_mode = loader.get_split_mode(data)
    
    if mode is None:
        return
        
    match mode:
        case "encryptrar":
            encrypt_with_rar_protocol(data, core)
        case "encrypt":
            if split_mode:
                encrypt_with_split_protocol(data, core)
            else:
                encrypt_protocol(data, core)
        case "decryptrar":
            decrypt_with_rar_protocol(data, core)
        case "decrypt":
            decrypt_protocol(data, core)
        case _:
            logging.warning(Msg.Warn.wrong_params) 