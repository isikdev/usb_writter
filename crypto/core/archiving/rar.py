import os
import subprocess
import rarfile
from crypto.wrappers.logging import logging
from crypto.constants import Msg
from crypto.core.par2 import creator as par2creator

def rar_container(raw_rar_data, par2_data, container_path: str) -> bool:
    """
    Создает RAR архив из контейнера
    
    Args:
        raw_rar_data: Данные для создания RAR архива
        par2_data: Данные для создания PAR2 файлов
        container_path: Путь к контейнеру
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    from crypto.config.loader import process_rar_data
    
    rar_data = process_rar_data(raw_rar_data)
    archive_path = rar_data["archive_path"]
    piece_size = rar_data["piece_size"]
    recovery_procent = rar_data["recovery_procent"]

    command = [
        "rar", "a",
        "-tsc",
        f"-v{piece_size}",
        f"-rr{recovery_procent}",
        "-y",
        archive_path,
        container_path
    ]

    logging.debug(f"Выполняю команду: {' '.join(command)}")

    if "password" in raw_rar_data:
        password = raw_rar_data["password"]
        command.insert(2, f"-p{password}")

    result = subprocess.run(command)
    if result.returncode != 0:
        logging.error(f"Ошибка при создании RAR архива: код {result.returncode}")
        return False

    if par2_data is not None:
        file_path = par2_data["file_path"]
        par2file_path = par2_data["par2file_path"]
        recovery_procent = par2_data["recovery_procent"]
        par2creator.make_par2(file_path, par2file_path, recovery_procent)
    return True

def unrar_container(raw_unrar_data, par2_data) -> bool:
    """
    Извлекает контейнер из RAR архива
    
    Args:
        raw_unrar_data: Данные для извлечения из RAR архива
        par2_data: Данные для проверки PAR2 файлов
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    from crypto.config.loader import process_unrar_data
    
    unrar_data = process_unrar_data(raw_unrar_data)
    first_archive_path = unrar_data["first_archive_path"]
    output = unrar_data["output"]

    if (not os.path.exists(first_archive_path)):
        logging.info(Msg.Info.first_archive_path_not_found(first_archive_path))
        return False

    if par2_data is not None:
        par2file_path = par2_data["par2file_path"]
        logging.info(Msg.Info.verifying_archive)
        if not par2creator.verify_files(par2file_path):
            exit(1)
    try:
        logging.info(Msg.Info.verifying_archive)
        logging.info(f"Извлечение в директорию: {output}")
        with rarfile.RarFile(first_archive_path) as rf:
            logging.info(f"Содержимое архива: {rf.namelist()}")
            for member in rf.namelist():
                # Извлекаем только имя файла без пути
                filename = os.path.basename(member)
                if filename:  # Пропускаем, если это директория (пустое имя файла)
                    if "password" in unrar_data:
                        source = rf.open(member, pwd=unrar_data["password"])
                    else:
                        source = rf.open(member)
                    target_path = os.path.join(output, filename)
                    with open(target_path, 'wb') as target:
                        target.write(source.read())
                    source.close()
            return True
    except rarfile.BadRarFile:
        logging.error(Msg.Err.bad_rarfile)
        return False
    except rarfile.RarWrongPassword:
        logging.error(Msg.Err.rarfile_wrongpas)
        return False
    except Exception as e:
        logging.error(Msg.Err.unrar_cont_error(e))
        return False 