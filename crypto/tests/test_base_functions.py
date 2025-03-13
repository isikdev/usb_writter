import pytest
from modules import aes
from modules import winDiskHandler
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@pytest.mark.parametrize("password", ["1234", "sdfdf", ""])
@pytest.mark.parametrize("is_disk", [True, False])
def test_aes(disk_path: str, temp_container: str, password: str, is_disk: bool) -> None:
    if is_disk and disk_path is None:
        pytest.skip("Disk path must be provided when isDisk=True")

    logger.info(f"Running test with {'disk' if is_disk else 'file'}")
    target_path = disk_path if is_disk else temp_container
    expected_data = b"Test data for encryption"

    if is_disk:
        handle = winDiskHandler.DiskHandler(target_path, 4096)
        handle.write_data(0, expected_data)
    else:
        assert os.path.exists(target_path)
        with open(target_path, "wb") as f:
            f.write(expected_data)

    aes_obj = aes.Aes(4096, is_disk)
    data_size = len(expected_data)

    logger.info("Encrypting container")
    aes_obj.process_file_part(target_path, password,
                              0, data_size, aes.Mode.Encrypt)

    logger.info("Decrypting container")
    aes_obj.process_file_part(target_path, password,
                              0, data_size, aes.Mode.Decrypt)

    if is_disk:
        data = handle.read_data(0, data_size)
    else:
        with open(target_path, "rb") as f:
            data = f.read()

    assert data == expected_data


@pytest.mark.parametrize("data_size", [32, 512])
@pytest.mark.parametrize("is_disk", [True, False])
def test_aes_different_sizes(disk_path: str, temp_container: str, random_data, data_size: int, is_disk: bool) -> None:
    if is_disk and disk_path is None:
        pytest.skip("Disk path must be provided when isDisk=True")

    data_512b, data_32b = random_data
    test_data = data_512b if data_size == 512 else data_32b
    test_data = test_data[:data_size]  # Ensure exact size

    target_path = disk_path if is_disk else temp_container

    if is_disk:
        handle = winDiskHandler.DiskHandler(target_path, 4096)
        handle.write_data(0, test_data)
    else:
        with open(temp_container, "wb") as f:
            f.write(test_data)

    aes_obj = aes.Aes(4096, is_disk)
    password = "test_password"

    logger.info(f"Testing {data_size}b {
                'disk' if is_disk else 'file'} encryption")
    aes_obj.process_file_part(target_path, password,
                              0, data_size, aes.Mode.Encrypt)
    aes_obj.process_file_part(target_path, password,
                              0, data_size, aes.Mode.Decrypt)

    if is_disk:
        result = handle.read_data(0, data_size)
    else:
        with open(temp_container, "rb") as f:
            result = f.read()

    assert result == test_data
