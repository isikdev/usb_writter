import os
import sys
import subprocess
import psutil
import ctypes
import ctypes.wintypes as wintypes


class AskInitiateDrive(Exception):
    def __init__(self):
        super().__init__("Have you initialized the device?(noise option)")

    def __str__(self):
        return f"{self.args[0]}"


class DiskHandler:
    SECTOR_SIZE = 512  # 512 Standard sector size
    BUFFER_SIZE = 128 * 1024
    GENERIC_WRITE = 0x40000000
    GENERIC_READ = 0x80000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    FILE_BEGIN = 0
    if sys.platform == 'win32':
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

    def __init__(self, disk_letter, buffer_size):
        self.disk_letter = disk_letter
        self.disk = self.open_disk()
        if buffer_size % self.SECTOR_SIZE != 0:
            print(f"the buffer size must be divisible by {self.SECTOR_SIZE}")
            raise
        self.BUFFER_SIZE = buffer_size

    def open_disk(self):
        hDevice = self.kernel32.CreateFileW(
            self.disk_letter,
            self.GENERIC_READ | self.GENERIC_WRITE,
            self.FILE_SHARE_READ | self.FILE_SHARE_WRITE,
            None,
            self.OPEN_EXISTING,
            0,
            None
        )

        if hDevice == self.INVALID_HANDLE_VALUE:
            raise ctypes.WinError(ctypes.get_last_error())

        return hDevice

    def close_disk(self):
        self.kernel32.CloseHandle(self.disk)

    def penetrateMSFSprotection(self):
        from . import penetrateFSprotection as penFS
        offset = 0
        size = 1024  # 1 KB for example

        try:
            hDevice = penFS.open_raw_disk(self.disk_letter)
            data_to_write = b'\x00' * size  # Example data to write
            penFS.write_raw_disk(hDevice, offset, data_to_write)
        except Exception:
            print("DISK ERROR: FAILED TO PENETRATE FS PROTECTION")
            raise
        finally:
            penFS.close_raw_disk(hDevice)

    def get_disk_size(self):
        if os.name == 'nt':
            if self.disk_letter.lower().startswith("physicaldrive"):
                self.penetrateMSFSprotection = lambda: None

            IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
            GENERIC_READ = 0x80000000
            FILE_SHARE_READ = 0x00000001
            FILE_SHARE_WRITE = 0x00000002
            OPEN_EXISTING = 3
            INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

            class GET_LENGTH_INFORMATION(ctypes.Structure):
                _fields_ = [("Length", ctypes.c_ulonglong)]

            # Open the disk
            handle = ctypes.windll.kernel32.CreateFileW(
                self.disk_letter,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )

            if handle == INVALID_HANDLE_VALUE:
                raise ctypes.WinError(ctypes.get_last_error())

            # Prepare the structure to receive the length information
            length_info = GET_LENGTH_INFORMATION()
            bytes_returned = wintypes.DWORD()

            # Call DeviceIoControl
            result = ctypes.windll.kernel32.DeviceIoControl(
                handle,
                IOCTL_DISK_GET_LENGTH_INFO,
                None,
                0,
                ctypes.byref(length_info),
                ctypes.sizeof(length_info),
                ctypes.byref(bytes_returned),
                None
            )

            # Close the handle
            ctypes.windll.kernel32.CloseHandle(handle)

            if not result:
                raise ctypes.WinError(ctypes.get_last_error())

            length_info.Length = self.BUFFER_SIZE * \
                (length_info.Length // self.BUFFER_SIZE)

            return length_info.Length

        else:
            try:
                # For Linux, handle both drive letters and physical drive paths
                disk_path = self.disk_letter
                if disk_path.startswith("\\\\.\\PhysicalDrive"):
                    # Convert Windows physical drive path to Linux format
                    drive_num = disk_path.split("PhysicalDrive")[1]
                    disk_path = f"/dev/sd{chr(ord('a') + int(drive_num))}"
                
                result = subprocess.run(
                    ["lsblk", "-bno", "SIZE", disk_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                size = int(result.stdout.strip())
                # Round down to nearest buffer size
                size = (size // self.BUFFER_SIZE) * self.BUFFER_SIZE
                return size
            except Exception as e:
                print(f"Error getting disk size: {e}")
                return None

    def set_file_pointer(self, offset):
        new_pointer = ctypes.c_longlong(offset)
        result = self.kernel32.SetFilePointerEx(
            self.disk, new_pointer, None, self.FILE_BEGIN)
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())

    def read_sector(self, sector_number, buffer_size):
        offset = sector_number * buffer_size
        self.set_file_pointer(offset)
        buffer = ctypes.create_string_buffer(buffer_size)
        bytesRead = ctypes.c_ulong(0)
        self.kernel32.ReadFile(
            self.disk, buffer, buffer_size, ctypes.byref(bytesRead), None)
        return buffer.raw

    def write_aligned_data(self, offset, data):
        self.set_file_pointer(offset)
        bytesWritten = ctypes.c_ulong(0)
        success = self.kernel32.WriteFile(self.disk, data, len(
            data), ctypes.byref(bytesWritten), None)
        if not success:
            print(ctypes.get_last_error())
            raise AskInitiateDrive

    def write_sector(self, sector_number, data):
        offset = sector_number * self.SECTOR_SIZE
        self.set_file_pointer(offset)
        bytesWritten = ctypes.c_ulong(0)
        success = self.kernel32.WriteFile(self.disk, data, len(
            data), ctypes.byref(bytesWritten), None)
        if not success:
            print(ctypes.get_last_error())
            raise AskInitiateDrive

    def write_data(self, offset, data):
        start_sector = offset // self.SECTOR_SIZE
        # Read and modify the first sector if needed
        if offset % self.SECTOR_SIZE != 0:
            sector_data = self.read_sector(start_sector, self.SECTOR_SIZE)
            start_offset = offset % self.SECTOR_SIZE
            part1 = sector_data[:start_offset]

            part2 = data[:self.SECTOR_SIZE - start_offset]
            part3 = sector_data[start_offset + len(part2):]

            new_sector_data = part1 + part2 + part3
            self.write_sector(start_sector, new_sector_data)
            data = data[self.SECTOR_SIZE - start_offset:]
            start_sector += 1

        # Write middle sectors directly
        while len(data) >= self.SECTOR_SIZE:
            self.write_sector(start_sector, data[:self.SECTOR_SIZE])
            data = data[self.SECTOR_SIZE:]
            start_sector += 1

        # Read and modify the last sector if needed
        if data:
            sector_data = self.read_sector(start_sector, self.SECTOR_SIZE)
            part1 = data
            part2 = sector_data[len(part1):]
            new_sector_data = part1 + part2
            self.write_sector(start_sector, new_sector_data)

    def read_data(self, offset, size):
        start_sector = offset // self.BUFFER_SIZE
        data = b''

        # Read the first sector if it's not fully aligned
        if offset % self.BUFFER_SIZE != 0:
            sector_data = self.read_sector(start_sector, self.BUFFER_SIZE)
            start_offset = offset % self.BUFFER_SIZE

            # Calculate how many bytes to read from the first sector
            bytes_to_read_from_first_sector = min(
                self.BUFFER_SIZE - start_offset, size)
            data += sector_data[start_offset:start_offset +
                                bytes_to_read_from_first_sector]

            # Reduce size by the bytes read from the first sector
            size -= bytes_to_read_from_first_sector

            # Move to the next sector if needed
            start_sector += 1

        # Read the middle sectors if any
        while size >= self.BUFFER_SIZE:
            sector_data = self.read_sector(start_sector, self.BUFFER_SIZE)
            data += sector_data
            size -= self.BUFFER_SIZE
            start_sector += 1

        # Read the last sector if there's remaining data
        if size > 0:
            sector_data = self.read_sector(start_sector, self.BUFFER_SIZE)
            # Read only the remaining bytes needed
            # Ensure we only read the requested amount
            data += sector_data[:size]

        return data


def write_file_to_disk(disk_path, file_path, offset):
    writer = DiskHandler(disk_path, 64 * 1024)

    file_size = os.path.getsize(file_path)

    with open(file_path, 'rb') as file:
        remaining_size = file_size
        while remaining_size > 0:
            print(f"fsize: {file_size}")
            read_size = min(writer.BUFFER_SIZE, remaining_size)
            print(f"rsize: {read_size}")
            file_data = file.read(read_size)

            writer.write_data(offset, file_data)
            offset += len(file_data)
            remaining_size -= read_size
            print(offset)

    return file_size


def read_file_from_disk(disk_path, output_file_path, offset, size):
    writer = DiskHandler(disk_path, 64 * 1024)

    with open(output_file_path, 'wb') as output_file:
        remaining_size = size
        current_offset = offset

        while remaining_size > 0:
            read_size = min(writer.BUFFER_SIZE, remaining_size)
            data = writer.read_data(current_offset, read_size)
            output_file.write(data)
            remaining_size -= read_size
            current_offset += read_size
