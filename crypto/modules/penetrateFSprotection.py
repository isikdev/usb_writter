import ctypes
import os

# Define constants
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
FILE_BEGIN = 0

# Load necessary functions from kernel32.dll
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)


def open_raw_disk(device_path):
    # Open the device
    hDevice = kernel32.CreateFileW(
        device_path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )

    if hDevice == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())

    return hDevice


def read_raw_disk(hDevice, offset, size):
    kernel32.SetFilePointer(hDevice, offset, None, FILE_BEGIN)
    buffer = ctypes.create_string_buffer(size)
    bytesRead = ctypes.c_ulong(0)
    success = kernel32.ReadFile(
        hDevice, buffer, size, ctypes.byref(bytesRead), None)
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.raw


def write_raw_disk(hDevice, offset, data):
    kernel32.SetFilePointer(hDevice, offset, None, FILE_BEGIN)
    bytesWritten = ctypes.c_ulong(0)
    success = kernel32.WriteFile(hDevice, data, len(
        data), ctypes.byref(bytesWritten), None)
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    return bytesWritten.value


def close_raw_disk(hDevice):
    kernel32.CloseHandle(hDevice)
