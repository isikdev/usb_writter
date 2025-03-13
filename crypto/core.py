import os
import sys
import secrets
import zlib
from modules import aes, winDiskHandler, zip, header
from modules.wrapers.logging import logging
from modules.constants import Msg, Def_val
from modules import config as conf
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


class Core:
    from utils.data_utils import parse_size

    container_path: str = Def_val.container_path
    size_of_new_container: int = parse_size(Def_val.new_container_size)
    block_size: int = parse_size(Def_val.block_size)
    buffer_size: int = parse_size(Def_val.buffer_size)
    disk_mode: bool = False

    def __init__(self, conf, disk_mode=False) -> None:
        from utils.data_utils import parse_size
        if "container_path" in conf:
            self.container_path = conf["container_path"]
        if "new_container_size" in conf:
            self.size_of_new_container = parse_size(conf["new_container_size"])
        if "block_size" in conf:
            self.block_size = parse_size(conf["block_size"])
        if "buffer_size" in conf:
            self.buffer_size = parse_size(conf["buffer_size"])

        self.disk_mode = disk_mode

    def set_disk_mode(self, mode: bool) -> None:
        self.disk_mode = mode

    def change_container_path(self, new_container_path: str) -> None:
        self.container_path = new_container_path

    def get_container_size(self) -> int | None:
        if self.container_path is None:
            return None

        if not self.disk_mode:
            if not os.path.exists(self.container_path):
                logging.error("Couldn't find container...")
                return None
            return os.path.getsize(self.container_path)
        else:
            handle = winDiskHandler.DiskHandler(
                self.container_path, self.buffer_size)
            container_size = handle.get_disk_size()
            return container_size

    def create_noise(self) -> None:
        bytes_to_write = self.get_container_size()
        if bytes_to_write is None:
            bytes_to_write = self.size_of_new_container
        parts = bytes_to_write // self.buffer_size
        additional = bytes_to_write % self.buffer_size

        if not self.disk_mode:
            with open(self.container_path, 'wb') as device:
                with aes.tqdm(total=bytes_to_write, desc=Msg.PBar.filling_container_with_noise, unit="B", unit_scale=True) as pbar:
                    for i in range(parts):
                        buffer = secrets.token_bytes(self.buffer_size)
                        device.write(buffer)
                        pbar.update(self.buffer_size)

                    if additional > 0:
                        buffer = secrets.token_bytes(additional)
                        device.write(buffer)
                        pbar.update(self.buffer_size)
        else:
            handle = winDiskHandler.DiskHandler(
                self.container_path, self.buffer_size)
            with aes.tqdm(total=bytes_to_write, desc=Msg.PBar.filling_container_with_noise, unit="B", unit_scale=True) as pbar:
                current_offset = 0
                for i in range(parts):
                    buffer = secrets.token_bytes(self.buffer_size)
                    handle.write_aligned_data(current_offset, buffer)
                    current_offset += self.buffer_size
                    pbar.update(self.buffer_size)

                if additional > 0:
                    buffer = secrets.token_bytes(additional)
                    handle.write_aligned_data(current_offset, buffer)
                    current_offset += additional
                    pbar.update(self.buffer_size)
            handle.close_disk()

    def get_iv(self, password: str) -> bytes:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.backends import default_backend

        def derive_iv(password, iv_iterations, iv_size):
            backend = default_backend()
            salt = password.encode()
            kdf_iv = PBKDF2HMAC(
                algorithm=hashes.SHA1(),
                length=iv_size,
                salt=salt,
                iterations=iv_iterations,
                backend=backend
            )
            return kdf_iv.derive(password.encode())
        iv_iterations = 12332
        iv_size = 16

        return derive_iv(
            password, iv_iterations, iv_size)

    def get_hashsum(self, start_pos: int, end_pos: int) -> str | None:
        if start_pos == end_pos:
            return None
        if start_pos < 0:
            start_pos = 0
        container_size = self.get_container_size()
        if end_pos > container_size:
            end_pos = container_size

        def align_data(pbar, handle, remaining_size, offset, current_offset, crc):
            sec_size = self.buffer_size
            start_pos = sec_size * (offset // sec_size)
            end_pos = start_pos + sec_size
            align_read_size = end_pos - offset

            read_size = min(align_read_size, remaining_size)
            chunk = handle.read_data(current_offset, read_size)
            current_offset += read_size
            remaining_size -= read_size
            pbar.update(read_size)

            return remaining_size, current_offset, zlib.crc32(chunk, crc)

        crc = 0
        total_size = end_pos - start_pos
        remaining_size = total_size

        with aes.tqdm(total=total_size, desc=Msg.PBar.fetching_container_hash, unit="B", unit_scale=True) as pbar:
            if not self.disk_mode:
                with open(self.container_path, "rb") as f:
                    f.seek(start_pos)
                    while remaining_size > 0:
                        read_size = min(self.buffer_size, remaining_size)
                        chunk = f.read(read_size)

                        remaining_size -= read_size
                        pbar.update(read_size)
                        if not chunk:
                            break
                        crc = zlib.crc32(chunk, crc)
            else:
                handle = winDiskHandler.DiskHandler(
                    self.container_path, self.buffer_size)
                current_offset = start_pos

                sec_size = self.buffer_size
                if start_pos % sec_size:
                    remaining_size, current_offset, crc = align_data(
                        pbar, handle, remaining_size, start_pos, current_offset, crc)

                while remaining_size > 0:
                    read_size = min(self.buffer_size, remaining_size)
                    chunk = handle.read_data(current_offset, read_size)
                    current_offset += read_size
                    remaining_size -= read_size
                    pbar.update(read_size)

                    crc = zlib.crc32(chunk, crc)
                handle.close_disk()
        return hex(crc & 0xffffffff)[2:]

    def get_container_parts(self, file_start_pos: int, file_end_pos: int, hashsum_limit: int):
        first_part_s = file_start_pos - 1 - hashsum_limit
        first_part_e = file_start_pos - 1
        first_part_hash = self.get_hashsum(first_part_s, first_part_e)

        second_part_s = file_end_pos + 1
        second_part_e = second_part_s + hashsum_limit
        second_part_hash = self.get_hashsum(second_part_s, second_part_e)

        return first_part_hash, second_part_hash

    def check_integrality(self, old_hashsum: str, new_hashsum: str, check_object: str) -> None:
        logging.info(f"Validating {check_object}")
        res = old_hashsum == new_hashsum
        if res:
            logging.info(Msg.Info.object_validated(check_object))
        else:
            logging.warning(Msg.Warn.object_not_validated(check_object))
            logging.warning(Msg.Warn.old_and_new_hash(
                old_hashsum, new_hashsum))

    def encrypt_archive(self, encrypt_config) -> None:
        from utils.data_utils import parse_size

        files = encrypt_config['files']
        directories = encrypt_config['directories']
        password = encrypt_config['password']
        hashsum_limit = 0
        if "hashsum_limit" in encrypt_config:
            hashsum_limit = parse_size(encrypt_config["hashsum_limit"])

        if not os.path.exists(self.container_path):
            self.create_noise()

        offset = len(password) * self.block_size
        passwd_offset = header.calculate_offset(password, 1024)
        header_size = passwd_offset + header.data_size
        iv = self.get_iv(password)

        extra_dir = conf.get_extradir(encrypt_config)
        if extra_dir != "":
            if not os.path.isdir(extra_dir):
                logging.warning(Msg.Warn.extra_dir_is_not_dir(extra_dir))

        archive_size = zip.zip_archive(
            self.container_path, offset + header_size, files, directories, extra_dir, self.buffer_size, self.disk_mode)

        old_first_part, old_second_part = self.get_container_parts(
            offset, offset + header_size + archive_size, hashsum_limit)

        header.write(self.container_path, offset, passwd_offset, iv,
                     archive_size, self.buffer_size, self.disk_mode)

        start_pos = offset + header_size
        end_pos = start_pos + archive_size

        aes_obj = aes.Aes(self.buffer_size, self.disk_mode)

        aes_obj.process_file_part(self.container_path, password,
                                  start_pos, end_pos, aes.Mode.Encrypt)

        new_first_part, new_second_part = self.get_container_parts(
            offset, offset + header_size + archive_size, hashsum_limit)
        if old_first_part is not None and new_first_part is not None:
            self.check_integrality(
                old_first_part, new_first_part, "The first part")
        if old_second_part is not None and new_second_part is not None:
            self.check_integrality(
                old_second_part, new_second_part, "The second part")

    def decrypt_archive(self, output_path: str, password: str) -> None:
        if not os.path.exists(self.container_path):
            aes.logging.error(Msg.Warn.container_doesnt_exist)
            return

        offset = len(password) * self.block_size
        passwd_offset = header.calculate_offset(password, 1024)
        header_size = passwd_offset + header.data_size
        iv = self.get_iv(password)

        ok, archive_size = header.read(
            self.container_path, offset, passwd_offset, iv, self.buffer_size, self.disk_mode)

        start_pos = offset + header_size
        end_pos = start_pos + archive_size
        aes_obj = aes.Aes(self.buffer_size, self.disk_mode)

        aes_obj.process_file_part(self.container_path, password,
                                  start_pos, end_pos, aes.Mode.Decrypt)

        if not ok:
            aes.logging.error(Msg.Err.wrong_pass)
            return

        zip.unzip_archive(self.container_path, offset + header_size,
                          offset + archive_size + header_size, output_path, self.buffer_size, self.disk_mode)

        aes_obj.process_file_part(self.container_path, password,
                                  start_pos, end_pos, aes.Mode.Encrypt)

    def encrypt_container(self, encrypt_config) -> None:
        if isinstance(encrypt_config, list):
            for encrypt_conf in encrypt_config:
                self.encrypt_archive(encrypt_conf)
        else:
            self.encrypt_archive(encrypt_config)

    def decrypt_container(self, output_path: str, decrypt_config, password) -> None:
        from utils.data_utils import parse_size
        hashsum_limit = 0
        if "hashsum_limit" in decrypt_config:
            hashsum_limit = parse_size(decrypt_config["hashsum_limit"])

        old_hashsum = self.get_hashsum(
            0, hashsum_limit)

        if isinstance(password, list):
            for passwd in password:
                self.decrypt_archive(output_path, passwd)
        else:
            self.decrypt_archive(output_path, password)

        new_hashsum = self.get_hashsum(0, hashsum_limit)

        if old_hashsum is not None and new_hashsum is not None:
            self.check_integrality(old_hashsum, new_hashsum, "Container")
