import io
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from enum import Enum
from tqdm import tqdm

from . import winDiskHandler
from .wrapers.logging import logging
from .constants import Msg


class Mode(Enum):
    Encrypt = 1
    Decrypt = 2


class Aes:
    key_iterations = 10000
    iv_iterations = 25000
    key_size = 64
    iv_size = 16

    def __init__(self, buffer_size: int = 128*1024, disk_mode: bool = False) -> None:
        self.buffer_size = buffer_size
        self.disk_mode = disk_mode

    def _derive_key_and_iv(self, password: str, key_iterations: int, iv_iterations: int, key_size: int, iv_size: int):
        backend = default_backend()
        salt = b""
        kdf_key = PBKDF2HMAC(
            algorithm=hashes.SHA1(), length=key_size,
            salt=salt,
            iterations=key_iterations,
            backend=backend
        )
        kdf_iv = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=iv_size,
            salt=salt,
            iterations=iv_iterations,
            backend=backend
        )
        key = kdf_key.derive(password.encode())
        iv = kdf_iv.derive(password.encode())
        return key, iv

    def process_file_part(self, file_path: str, password: str, start_pos: int, end_pos: int, mode) -> None:
        key, iv = self._derive_key_and_iv(
            password, self.key_iterations, self.iv_iterations, self.key_size, self.iv_size)
        key1 = key[:32]
        key2 = key[32:]

        xts_key = key1 + key2

        self.cipher = Cipher(algorithms.AES(xts_key), modes.XTS(iv),
                             backend=default_backend())

        match mode:
            case Mode.Encrypt:
                self._encrypt(file_path, start_pos, end_pos)
            case Mode.Decrypt:
                self._decrypt(file_path, start_pos, end_pos)
            case _:
                logging.error(f"unknown mode [{mode}]")

    def _encrypt(self, file_path: str, start_pos: int, end_pos: int) -> None:
        encryptor = self.cipher.encryptor()
        total_size = end_pos - start_pos

        if not self.disk_mode:
            with open(file_path, 'r+b') as f:
                f.seek(start_pos)
                remaining_size = total_size

                with tqdm(total=total_size, desc=Msg.PBar.encrypting_part, unit="B", unit_scale=True) as pbar:
                    while remaining_size > 0:
                        to_read = min(self.buffer_size, remaining_size)
                        file_block = f.read(to_read)

                        if not file_block:
                            break

                        encrypted_block = encryptor.update(file_block)

                        f.seek(-len(file_block), io.SEEK_CUR)
                        f.write(encrypted_block)

                        remaining_size -= len(file_block)
                        pbar.update(len(file_block))

                    final_block = encryptor.finalize()
                    f.write(final_block)
                    pbar.update(len(final_block))
        else:
            handle = winDiskHandler.DiskHandler(file_path, self.buffer_size)
            current_offset = start_pos
            remaining_size = total_size

            def align_data(pbar, handle):
                nonlocal remaining_size, current_offset

                start_A_pos = sec_size * (start_pos // sec_size)
                end_A_pos = start_A_pos + sec_size
                align_read_size = end_A_pos - start_pos

                to_read = min(remaining_size, align_read_size)
                file_block = handle.read_data(current_offset, to_read)

                if not file_block:
                    return

                encrypted_block = encryptor.update(file_block)

                handle.write_data(current_offset, encrypted_block)

                current_offset += len(file_block)
                remaining_size -= len(file_block)
                pbar.update(len(file_block))

            with tqdm(total=total_size, desc=Msg.PBar.encrypting_part, unit="B", unit_scale=True) as pbar:
                sec_size = self.buffer_size
                if start_pos % sec_size:
                    align_data(pbar, handle)

                while remaining_size > 0:
                    to_read = min(self.buffer_size, remaining_size)
                    file_block = handle.read_data(current_offset, to_read)

                    if not file_block:
                        break

                    encrypted_block = encryptor.update(file_block)

                    if to_read % 512 == 0:
                        handle.write_aligned_data(
                            current_offset, encrypted_block)
                    else:
                        handle.write_data(current_offset, encrypted_block)

                    current_offset += len(file_block)
                    remaining_size -= len(file_block)
                    pbar.update(len(file_block))

                final_block = encryptor.finalize()
                handle.write_data(current_offset, final_block)
                pbar.update(len(final_block))
                handle.close_disk()

    def _decrypt(self, file_path: str, start_pos: int, end_pos: int) -> None:
        decryptor = self.cipher.decryptor()
        total_size = end_pos - start_pos
        with open(file_path, 'r+b') as f:
            remaining_size = total_size

            if not self.disk_mode:
                f.seek(start_pos)
                with tqdm(total=total_size, desc=Msg.PBar.decrypting_part, unit="B", unit_scale=True) as pbar:
                    while remaining_size > 0:
                        to_read = min(self.buffer_size, remaining_size)
                        encrypted_block = f.read(to_read)

                        if not encrypted_block:
                            break

                        decrypted_block = decryptor.update(encrypted_block)

                        f.seek(-len(encrypted_block), io.SEEK_CUR)
                        f.write(decrypted_block)

                        remaining_size -= len(decrypted_block)
                        pbar.update(len(encrypted_block))

                    final_block = decryptor.finalize()
                    f.write(final_block)
                    pbar.update(len(final_block))
            else:
                handle = winDiskHandler.DiskHandler(
                    file_path, self.buffer_size)
                current_offset = start_pos
                remaining_size = total_size

                def align_data(pbar, handle):
                    nonlocal remaining_size, current_offset

                    start_A_pos = sec_size * (start_pos // sec_size)
                    end_A_pos = start_A_pos + sec_size
                    align_read_size = end_A_pos - start_pos

                    to_read = min(remaining_size, align_read_size)
                    encrypted_block = handle.read_data(current_offset, to_read)

                    if not encrypted_block:
                        return

                    decrypted_block = decryptor.update(encrypted_block)

                    handle.write_data(current_offset, decrypted_block)

                    current_offset += len(decrypted_block)
                    remaining_size -= len(decrypted_block)
                    pbar.update(len(encrypted_block))

                with tqdm(total=total_size, desc=Msg.PBar.decrypting_part, unit="B", unit_scale=True) as pbar:
                    sec_size = self.buffer_size
                    if start_pos % sec_size:
                        align_data(pbar, handle)
                    while remaining_size > 0:
                        to_read = min(self.buffer_size, remaining_size)
                        encrypted_block = handle.read_data(
                            current_offset, to_read)

                        if not encrypted_block:
                            break

                        decrypted_block = decryptor.update(encrypted_block)

                        if to_read % 512 == 0:
                            handle.write_aligned_data(
                                current_offset, decrypted_block)
                        else:
                            handle.write_data(current_offset, decrypted_block)

                        current_offset += len(decrypted_block)
                        remaining_size -= len(decrypted_block)
                        pbar.update(len(encrypted_block))

                    final_block = decryptor.finalize()
                    handle.write_data(current_offset, final_block)
                    pbar.update(len(final_block))
                handle.close_disk()
