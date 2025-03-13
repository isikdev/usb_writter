import hashlib
from . import winDiskHandler

data_size = 16 + 8


def calculate_offset(password, max_size):
    password_bytes = password.encode('utf-8')
    sha256_hash = hashlib.sha256(password_bytes).hexdigest()
    hash_value = int(sha256_hash[:8], 16)
    offset = hash_value % max_size + 1

    return offset


def write(container_path, offset, passwd_offset, iv, archive_size, buffer_size, isDisk):
    if not isDisk:
        with open(container_path, 'rb+') as file:
            file.seek(offset + passwd_offset)
            file.write(iv)
            size_bytes = bytearray(8)
            for i in range(8):
                size_bytes[i] = (archive_size >> 8 * (7 - i)) & 0xFF
            file.write(size_bytes)
    else:
        handle = winDiskHandler.DiskHandler(container_path, buffer_size)
        current_offset = offset + passwd_offset
        handle.write_data(current_offset, iv)
        current_offset += 16
        size_bytes = bytearray(8)
        for i in range(8):
            size_bytes[i] = (archive_size >> 8 * (7 - i)) & 0xFF
        handle.write_data(current_offset, size_bytes)
        handle.close_disk()


def read(container_path, offset, passwd_offset, iv, buffer_size, isDisk):
    if not isDisk:
        with open(container_path, 'rb') as file:
            file.seek(offset + passwd_offset)
            header_iv = file.read(16)
            header_size = file.read(8)
            size = 0
            for byte in header_size:
                size = (size << 8) + byte

            header_size = passwd_offset + data_size
            if header_iv != iv:
                return False, size
            return True, size
    else:
        handle = winDiskHandler.DiskHandler(container_path, buffer_size)
        current_offset = offset + passwd_offset
        header_iv = handle.read_data(current_offset, 16)
        current_offset += 16
        header_size = handle.read_data(current_offset, 8)
        size = 0
        for byte in header_size:
            size = (size << 8) + byte

        header_size = passwd_offset + data_size
        handle.close_disk()
        if header_iv != iv:
            return False, size
        return True, size
