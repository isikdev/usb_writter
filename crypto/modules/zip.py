import zipfile
import rarfile
import io
import os
import subprocess
import shutil
from tqdm import tqdm
import tempfile
from modules import winDiskHandler
from .constants import Msg
from .wrapers.logging import logging
from .config import process_rar_data, process_unrar_data
from . import par2deep

SECRET_EXTENSION = ".secret_shh"

def rar_container(raw_rar_data, par2_data, container_path: str) -> bool:
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

    print(command)

    if "password" in raw_rar_data:
        password = raw_rar_data["password"]
        command.insert(2, f"-p{password}")

    result = subprocess.run(command)
    if result.returncode != 0:
        return False

    if par2_data is not None:
        file_path = par2_data["file_path"]
        par2file_path = par2_data["par2file_path"]
        recovery_procent = par2_data["recovery_procent"]
        par2deep.make_par2(file_path, par2file_path, recovery_procent)
    return True

def unrar_container(raw_unrar_data, par2_data) -> bool:
    unrar_data = process_unrar_data(raw_unrar_data)
    first_archive_path = unrar_data["first_archive_path"]
    output = unrar_data["output"]

    if (not os.path.exists(first_archive_path)):
        logging.info(Msg.Info.first_archive_path_not_found(first_archive_path))
        return False

    if par2_data is not None:
        par2file_path = par2_data["par2file_path"]
        logging.info(Msg.Info.verifying_archive)
        if not par2deep.verify_files(par2file_path):
            exit(1)
    try:
        logging.info(Msg.Info.verifying_archive)
        logging.info(f"Extracting to directory: {output}")
        with rarfile.RarFile(first_archive_path) as rf:
            logging.info(f"Archive contents: {rf.namelist()}")
            for member in rf.namelist():
                # Extract only the filename without path
                filename = os.path.basename(member)
                if filename:  # Skip if it's a directory (empty filename)
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

def read_archive(container_path: str, offset: int, size: int, buffer_size: int, isDisk: bool) -> None:
    temp_file = None
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        if not isDisk:
            with open(container_path, 'rb') as container:
                container.seek(offset)
                remaining_size = size - offset

                with tqdm(total=remaining_size, desc=Msg.PBar.loading_archive, unit="B", unit_scale=True) as pbar:
                    while remaining_size > 0:
                        read_size = min(buffer_size, remaining_size)
                        data = container.read(read_size)
                        temp_file.write(data)
                        remaining_size -= read_size
                        pbar.update(read_size)
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

                pbar.update(read_size)

            with tqdm(total=remaining_size, desc=Msg.PBar.loading_archive, unit="B", unit_scale=True) as pbar:
                if offset % sec_size:
                    align_data(pbar, handle)
                while remaining_size > 0:
                    read_size = min(buffer_size, remaining_size)
                    data = handle.read_data(current_offset, read_size)
                    current_offset += read_size
                    temp_file.write(data)
                    remaining_size -= read_size
                    pbar.update(read_size)

            handle.close_disk()
        return temp_file
    except Exception as e:
        logging.error(Msg.Err.reading_archive_error(e))
        if temp_file:
            temp_file.close()
            os.remove(temp_file.name)

def extra_decompress(archive_path: str, output_path: str) -> None:
    dir_path = archive_path.replace(SECRET_EXTENSION, "")
    output_dir_path = os.path.join(output_path, dir_path)

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
    temp_file = None
    extra_file = ""
    try:
        temp_file = read_archive(container_path, offset, size, buffer_size, isDisk)
        with zipfile.ZipFile(temp_file.name, 'r') as zipf:
            file_list = zipf.namelist()
            with tqdm(total=len(file_list), desc=Msg.PBar.extracting_file, unit="file") as pbar:
                for file_to_extract in file_list:
                    root, extension = os.path.splitext(file_to_extract)
                    if extension == SECRET_EXTENSION:
                        zipf.extract(file_to_extract, path=".")
                        extra_file = file_to_extract
                        extra_decompress(extra_file, output_path)
                        pbar.update(1)
                        continue
                    zipf.extract(file_to_extract, path=output_path)
                    logging.info(Msg.Info.file_extracted(file_to_extract))
                    pbar.update(1)
    except Exception as e:
        logging.error(Msg.Err.processing_archive_error(e))
    finally:
        if temp_file:
            temp_file.close()
            os.remove(temp_file.name)
            if os.path.exists(extra_file):
                os.remove(extra_file)

def write_zip_to_cont(container_path: str, zip_path: str, offset: int, buffer_size: int, isDisk: bool) -> int:

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

            pbar.update(read_size)

        with tqdm(total=remaining_size, desc=Msg.PBar.uploading_archive_to_disk, unit="B", unit_scale=True) as pbar:
            if not isDisk:
                with open(container_path, 'r+b') as container:
                    container.seek(offset)
                    while remaining_size > 0:
                        read_size = min(buffer_size, remaining_size)
                        archive_data = f.read(read_size)

                        container.write(archive_data)
                        remaining_size -= read_size
                        bytes_written += read_size
                        pbar.update(read_size)
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
                        pbar.update(read_size)
                except Exception as e:
                    logging.error(Msg.Err.writing_to_disk_error(e))
                    handle.close_disk()
                    return 0
                handle.close_disk()

        return bytes_written

def process_subdirs(root, sub_dirs, zipf) -> None:
    for sub_dir in sub_dirs:
        sub_dir_path = os.path.join(root, sub_dir)
        arcname = os.path.relpath(
            sub_dir_path, start=os.path.dirname(sub_dir)) + '/'
        zipf.writestr(arcname, '')
        logging.info(Msg.Info.added_directory(sub_dir_path))


def process_subfiles(root, dir, files, zipf, pbar) -> bool:
    is_empty = True
    for file in files:
        is_empty = False
        file_path = os.path.join(root, file)
        arcname = os.path.relpath(
            file_path, start=os.path.dirname(dir))
        try:
            zipf.write(file_path, arcname)
            logging.info(
                Msg.Info.added_file(file_path))
            pbar.update(1)
        except Exception as e:
            logging.error(Msg.Err.adding_file_error(file_path, e))
            return False
    return is_empty

def extra_compress(dictionary_size: str, dir_path: str, archive_name: str, zipf) -> None:
    command = ['rar', 'a', '-m5', '-s', '-md' + dictionary_size, archive_name, dir_path]    

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            zipf.write(archive_name, os.path.basename(archive_name))
            logging.info(Msg.Info.added_directory(dir_path))
        if result.returncode != 0:
            logging.error(Msg.Err.adding_directory_to_archive_error(dir_path, result.stderr))
    except Exception as e:
        logging.error(Msg.Err.adding_directory_to_archive_error(dir_path, e))
    finally:
        if os.path.exists(archive_name):
            os.remove(archive_name)


def zip_archive(container_path: str, offset: int, files, directories, extra_dir: str, buffer_size: int, isDisk: bool) -> int:
    bytes_written = 0

    def check_archive(zipf):
        logging.info(Msg.Info.validating_archive)
        res = zipf.testzip()
        if res is None:
            logging.info(Msg.Info.archive_validated)
        else:
            logging.warning(Msg.Warn.archive_integrity_check_failed(res))

    #temp_file = tempfile.NamedTemporaryFile(delete=False)
    tempfile = "temp.zip"
    try:
        with zipfile.ZipFile(tempfile, 'w', zipfile.ZIP_DEFLATED) as zipf:

            total_files = len(files) + sum(len(files)
                                           for d in directories for _, _, files in os.walk(d))

            if extra_dir != "" and os.path.isdir(extra_dir):
                total_files += 1

            with tqdm(total=total_files, desc=Msg.PBar.adding_to_archive, unit="file") as pbar:
                for file in files:
                    if file != "":
                        try:
                            zipf.write(file, os.path.basename(file))
                            logging.info(Msg.Info.file_added_to_archive(file))
                            pbar.update(1)
                        except Exception as e:
                            logging.error(
                                Msg.Err.adding_file_to_archive_error(file, e))
                            return 0

                for dir in directories:
                    if os.path.isdir(dir):
                        is_empty = True
                        for root, sub_dirs, files in os.walk(dir):
                            process_subdirs(root, sub_dirs, zipf)
                            is_empty = process_subfiles(
                                root, dir, files, zipf, pbar)
                        if is_empty:
                            arcname = os.path.relpath(
                                dir, start=os.path.dirname(dir)) + '/'
                            zipf.writestr(arcname, '')
                            logging.info(Msg.Info.added_directory(dir))

                if os.path.isdir(extra_dir):
                    archive_name = os.path.basename(extra_dir) + SECRET_EXTENSION
                    extra_compress("524m", extra_dir, archive_name, zipf)
                    pbar.update(1)



            check_archive(zipf)
    except Exception as e:
        logging.error(Msg.Err.processing_archive_error(e))
        return 0
    finally:
        bytes_written = write_zip_to_cont(container_path, tempfile, offset, buffer_size, isDisk)
        os.remove(tempfile)
        return bytes_written