import os
import zipfile
import tempfile
import shutil
import subprocess
from tqdm import tqdm
from ...wrappers.logging import logging
from ...constants import Msg
from .. import winDiskHandler

SECRET_EXTENSION = ".secret_shh"

def read_archive(container_path: str, offset: int, size: int, buffer_size: int, isDisk: bool) -> tempfile.NamedTemporaryFile:
    """
    Читает архив из контейнера
    
    Args:
        container_path: Путь к контейнеру
        offset: Смещение в контейнере
        size: Размер архива
        buffer_size: Размер буфера для чтения
        isDisk: Флаг, указывающий, является ли контейнер диском
        
    Returns:
        tempfile.NamedTemporaryFile: Временный файл с содержимым архива
    """
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        if not isDisk:
            with open(container_path, 'rb') as container:
                container.seek(offset)
                remaining_size = size - offset

                with tqdm(total=remaining_size, desc=Msg.PBar.loading_archive, unit="%", unit_scale=False) as pbar:
                    while remaining_size > 0:
                        read_size = min(buffer_size, remaining_size)
                        data = container.read(read_size)
                        temp_file.write(data)
                        remaining_size -= read_size
                        progress_pct = 100 - (remaining_size / (size - offset) * 100)
                        pbar.update(progress_pct - pbar.n)
        else:
            handle = winDiskHandler.DiskHandler(container_path, buffer_size)
            remaining_size = size - offset
            current_offset = offset
            sec_size = buffer_size

            def align_data(pbar, handle):
                nonlocal remaining_size, current_offset

                start_pos = sec_size * (offset // sec_size)
                end_pos = start_pos + sec_size
                align_read_size = end_pos - offset

                read_size = min(align_read_size, remaining_size)
                data = handle.read_data(current_offset, read_size)
                temp_file.write(data)
                current_offset += read_size
                remaining_size -= read_size

                progress_pct = 100 - (remaining_size / (size - offset) * 100)
                pbar.update(progress_pct - pbar.n)

            with tqdm(total=100, desc=Msg.PBar.loading_archive, unit="%", unit_scale=False) as pbar:
                if offset % sec_size:
                    align_data(pbar, handle)
                while remaining_size > 0:
                    read_size = min(buffer_size, remaining_size)
                    data = handle.read_data(current_offset, read_size)
                    current_offset += read_size
                    temp_file.write(data)
                    remaining_size -= read_size
                    progress_pct = 100 - (remaining_size / (size - offset) * 100)
                    pbar.update(progress_pct - pbar.n)

            handle.close_disk()
        return temp_file
    except Exception as e:
        logging.error(Msg.Err.reading_archive_error(e))
        if temp_file:
            temp_file.close()
            os.remove(temp_file.name)
        return None

def extra_decompress(archive_path: str, output_path: str) -> None:
    """
    Распаковывает дополнительно сжатые файлы
    
    Args:
        archive_path: Путь к архиву
        output_path: Путь для извлечения
    """
    dir_path = archive_path.replace(SECRET_EXTENSION, "")
    output_dir_path = os.path.join(output_path, os.path.basename(dir_path))

    if os.path.exists(output_dir_path):
        shutil.rmtree(output_dir_path)

    command = ['rar', 'x', archive_path, output_path]

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(Msg.Info.extracted_directory(dir_path))
        if result.returncode != 0:
            logging.error(Msg.Err.extracting_directory_error(result.stderr))
    except Exception as e:
        logging.error(Msg.Err.extracting_directory_error(e))

def unzip_archive(container_path: str, offset: int, size: int, output_path: str, buffer_size: int, isDisk: bool) -> None:
    """
    Распаковывает ZIP архив из контейнера
    
    Args:
        container_path: Путь к контейнеру
        offset: Смещение в контейнере
        size: Размер архива
        output_path: Путь для извлечения
        buffer_size: Размер буфера для чтения
        isDisk: Флаг, указывающий, является ли контейнер диском
    """
    temp_file = None
    extra_file = ""
    try:
        temp_file = read_archive(container_path, offset, size, buffer_size, isDisk)
        if not temp_file:
            return
            
        with zipfile.ZipFile(temp_file.name, 'r') as zipf:
            file_list = zipf.namelist()
            with tqdm(total=100, desc=Msg.PBar.extracting_file, unit="%", unit_scale=False) as pbar:
                total_files = len(file_list)
                for i, file_to_extract in enumerate(file_list):
                    root, extension = os.path.splitext(file_to_extract)
                    if extension == SECRET_EXTENSION:
                        zipf.extract(file_to_extract, path=".")
                        extra_file = file_to_extract
                        extra_decompress(extra_file, output_path)
                    else:
                        zipf.extract(file_to_extract, path=output_path)
                        logging.info(Msg.Info.file_extracted(file_to_extract))
                    
                    progress_pct = (i + 1) / total_files * 100
                    pbar.update(progress_pct - pbar.n)
    except Exception as e:
        logging.error(Msg.Err.processing_archive_error(e))
    finally:
        if temp_file:
            temp_file.close()
            os.remove(temp_file.name)
            if os.path.exists(extra_file):
                os.remove(extra_file)

def write_zip_to_cont(container_path: str, zip_path: str, offset: int, buffer_size: int, isDisk: bool) -> int:
    """
    Записывает ZIP архив в контейнер
    
    Args:
        container_path: Путь к контейнеру
        zip_path: Путь к ZIP архиву
        offset: Смещение в контейнере
        buffer_size: Размер буфера для записи
        isDisk: Флаг, указывающий, является ли контейнер диском
        
    Returns:
        int: Количество записанных байт
    """
    with open(zip_path, 'rb') as f:
        f.seek(0)
        remaining_size = os.fstat(f.fileno()).st_size
        current_offset = 0
        bytes_written = 0

        def align_data(pbar, handle):
            nonlocal remaining_size, current_offset, bytes_written

            start_pos = sec_size * (offset // sec_size)
            end_pos = start_pos + sec_size
            align_read_size = end_pos - offset

            read_size = min(align_read_size, remaining_size)
            archive_data = f.read(read_size)
            handle.write_data(
                offset, archive_data)
            current_offset += read_size
            remaining_size -= read_size
            bytes_written += read_size

            progress_pct = 100 - (remaining_size / os.fstat(f.fileno()).st_size * 100)
            pbar.update(progress_pct - pbar.n)

        with tqdm(total=100, desc=Msg.PBar.uploading_archive_to_disk, unit="%", unit_scale=False) as pbar:
            if not isDisk:
                with open(container_path, 'r+b') as container:
                    container.seek(offset)
                    while remaining_size > 0:
                        read_size = min(buffer_size, remaining_size)
                        archive_data = f.read(read_size)

                        container.write(archive_data)
                        remaining_size -= read_size
                        bytes_written += read_size
                        progress_pct = 100 - (remaining_size / os.fstat(f.fileno()).st_size * 100)
                        pbar.update(progress_pct - pbar.n)
            else:
                handle = winDiskHandler.DiskHandler(
                    container_path, buffer_size)
                try:
                    sec_size = handle.SECTOR_SIZE
                    if offset % sec_size:
                        align_data(pbar, handle)
                    while remaining_size > 0:
                        read_size = min(buffer_size, remaining_size)
                        archive_data = f.read(read_size)

                        if read_size % sec_size == 0:
                            handle.write_aligned_data(
                                offset + current_offset, archive_data)
                        else:
                            handle.write_data(
                                offset + current_offset, archive_data)
                        current_offset += read_size
                        remaining_size -= read_size
                        bytes_written += read_size
                        progress_pct = 100 - (remaining_size / os.fstat(f.fileno()).st_size * 100)
                        pbar.update(progress_pct - pbar.n)
                finally:
                    handle.close_disk()
    return bytes_written