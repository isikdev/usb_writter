import pytest
import os
import random
import string
import shutil
from modules import par2deep, zip
from utils import hash_utils
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_DIR = "tests/test_rar_par2_output/"

def create_test_file(test_dir: str, size: int = 1024) -> str:
    """Create a test file with random binary content"""
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    file_path = os.path.join(test_dir, "test.bin")  
    with open(file_path, 'wb') as f:
        f.write(os.urandom(size))  
    return file_path

def clean_test_dir(test_dir: str):
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

def create_clean_test_file(test_dir: str, size: int = 1024) -> tuple[str, str]:
    """Create a clean test file and return its path and hash"""
    clean_test_dir(test_dir)
    test_file = create_test_file(test_dir)
    original_hash = hash_utils.calculate_file_hash(test_file)
    return test_file, original_hash

def corrupt_file(file_path: str, corruption_size: int = 50):
    """Corrupt a portion of the file"""
    file_size = os.path.getsize(file_path)
    corruption_pos = random.randint(0, max(1, file_size - corruption_size))
    
    with open(file_path, 'r+b') as f:
        f.seek(corruption_pos)
        f.write(os.urandom(corruption_size))


def test_rar_only():
    """Test RAR archiving without PAR2"""
    test_file, original_hash = create_clean_test_file(TEST_DIR)

    # RAR configuration
    rar_data = {
        "archive_path": os.path.join(TEST_DIR, "archive.rar"),
        "piece_size": "1m",
        "recovery_procent": 5,
        "password": "test_password"
    }
    
    # Archive and extract
    assert zip.rar_container(rar_data, None, test_file)
    os.remove(test_file)  
    
    # Extract and verify
    unrar_data = {
        "first_archive_path": rar_data["archive_path"],
        "output": TEST_DIR,
        "password": rar_data["password"]
    }
    assert zip.unrar_container(unrar_data, None)

    # Verify hash
    extracted_hash = hash_utils.calculate_file_hash(test_file)
    clean_test_dir(TEST_DIR)

    assert original_hash == extracted_hash

def test_par2_only():
    """Test PAR2 protection without RAR"""
    test_file, original_hash = create_clean_test_file(TEST_DIR)
    
    # Create PAR2 files 
    par2_data = {
        "file_path": test_file,
        "par2file_path": test_file + ".par2",
        "recovery_procent": 20  
    }
    
    assert par2deep.make_par2(
        par2_data["file_path"],
        par2_data["par2file_path"],
        par2_data["recovery_procent"]
    )
    
    # Corrupt the file and verify/repair
    corrupt_file(test_file, corruption_size=50)  
    assert par2deep.verify_files(par2_data["par2file_path"])
    
    # Verify hash after repair
    repaired_hash = hash_utils.calculate_file_hash(test_file)
    clean_test_dir(TEST_DIR)

    assert original_hash == repaired_hash

def test_rar_and_par2():
    """Test combination of RAR and PAR2"""
    test_file, original_hash = create_clean_test_file(TEST_DIR)

    # RAR configuration
    rar_data = {
        "archive_path": os.path.join(TEST_DIR, "archive.rar"),
        "piece_size": "1m",
        "recovery_procent": 5,
        "password": "test_password"
    }
    
    # PAR2 configuration 
    par2_data = {
        "file_path": rar_data["archive_path"],
        "par2file_path": rar_data["archive_path"] + ".par2",
        "recovery_procent": 20  
    }
    
    # Create RAR archive with PAR2
    assert zip.rar_container(rar_data, par2_data, test_file)
    os.remove(test_file)  
    
    # Corrupt the RAR archive
    corrupt_file(rar_data["archive_path"], corruption_size=50)  
    
    # Extract with PAR2 verification and repair
    unrar_data = {
        "first_archive_path": rar_data["archive_path"],
        "output": TEST_DIR,
        "password": rar_data["password"]
    }
    assert zip.unrar_container(unrar_data, par2_data)
    
    # Verify final hash
    extracted_hash = hash_utils.calculate_file_hash(test_file)
    clean_test_dir(TEST_DIR)
    assert original_hash == extracted_hash
