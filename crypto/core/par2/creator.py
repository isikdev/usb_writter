import os
import subprocess
import glob
from crypto.wrappers.logging import logging
from crypto.constants import Msg

def make_par2(file_path: str, parfile_name: str, recovery_percent: int) -> bool:
    """
    Создает PAR2 файлы для указанного файла или директории
    
    Args:
        file_path: Путь к файлу или директории
        parfile_name: Имя PAR2 файла
        recovery_percent: Процент восстановления
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    command = [
        "par2", "create",
        f"-r{recovery_percent}",
        parfile_name,
        file_path
    ]

    logging.debug(f"Выполняю команду: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode != 0:
        logging.error(f"Ошибка при создании PAR2 файлов: код {result.returncode}")
        return False
    logging.info(f"PAR2 файлы успешно созданы для {file_path}")
    return True

def repair_files(parfile_name: str) -> bool:
    """
    Восстанавливает поврежденные файлы с помощью PAR2
    
    Args:
        parfile_name: Имя PAR2 файла
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    command = [
        "par2", "repair",
        parfile_name
    ]

    logging.debug(f"Выполняю команду: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode != 0:
        logging.error(f"Ошибка при восстановлении файлов: код {result.returncode}")
        return False
    logging.info(f"Файлы успешно восстановлены с помощью {parfile_name}")
    return True

def verify_files(parfile_name: str) -> bool:
    """
    Проверяет целостность файлов с помощью PAR2
    
    Args:
        parfile_name: Имя PAR2 файла
        
    Returns:
        bool: True если файлы целы или успешно восстановлены, иначе False
    """
    command = [
        "par2", "verify",
        parfile_name
    ]

    logging.debug(f"Выполняю команду: {' '.join(command)}")
    result = subprocess.run(command)
    if result.returncode != 0:
        logging.info(f"Обнаружены повреждения, пытаюсь восстановить файлы")
        return repair_files(parfile_name)
    logging.info(f"Проверка целостности файлов успешно завершена")
    return True

def clean_old_par2(par2file_path: str) -> None:
    """
    Удаляет старые PAR2 файлы
    
    Args:
        par2file_path: Базовый путь к PAR2 файлам
    """
    directory = os.path.dirname(par2file_path)
    if not directory:
        directory = "."
    pattern = os.path.join(directory, "*.par2")

    if os.path.exists(par2file_path):
        logging.info(Msg.Info.deleting_old_par2)
        for par2file in glob.glob(pattern):
            os.remove(par2file)
            logging.info(Msg.Info.deleted_old_par2(par2file)) 