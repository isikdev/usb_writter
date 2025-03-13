import tempfile
import re
import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def pytest_addoption(parser):
    parser.addoption(
        "--disk-path", action="store",
        default=None,
        help="Path to the disk for tests when isDisk=True"
    )
    parser.addoption(
        "--password-count", action="store",
        default=1,
        type=int,
        help="Number of passwords to generate for fullscale decrypt test"
    )


@pytest.fixture
def disk_path(request):
    disk_path = request.config.getoption("--disk-path")
    if disk_path is None:
        return None
    if re.fullmatch(r"[A-Za-z]:", disk_path):
        container_path = rf"\\.\{disk_path}"
        return container_path
    else:
        return None


@pytest.fixture
def temp_container():
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp_path = temp.name
    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.fixture
def random_data():
    data_512b = os.urandom(512)
    data_non_512b = os.urandom(32)

    return data_512b, data_non_512b


@pytest.fixture
def password_count(request):
    """Returns the number of passwords to generate for fullscale decrypt test"""
    return request.config.getoption("--password-count")


@pytest.fixture
def configs_paths():
    from utils import file_utils, configs_utils

    txt_conf_dir = "tests/configs_txt/"
    json_conf_dir = "tests/configs_json/"

    txt_confs_paths = file_utils.get_files_from_dir(txt_conf_dir)
    json_confs_paths = file_utils.get_files_from_dir(json_conf_dir)

    txt_confs = configs_utils.get_confs(txt_confs_paths)
    json_confs = configs_utils.get_confs(json_confs_paths)

    return txt_confs, json_confs
