import pytest
import logging
import os
import shutil
from modules import config
from core import Core
from utils import hash_utils, file_utils


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def clean_output_dir(output_dir):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

@pytest.mark.parametrize("disk_mode", [False, True])
def test_decryption(configs_paths, disk_mode, disk_path, password_count):
    txt_confs, _ = configs_paths
    output_dir = "tests/test_output/"

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    assert txt_confs is not None

    for txt_conf_tupl in txt_confs:
        conf_name = txt_conf_tupl[0].name
        conf = txt_conf_tupl[1]
        assert conf is not None
        assert config.does_exist(
            "encrypt", conf), "Where's encrypt sector?"
        assert config.does_exist(
            "decrypt", conf), "Where's decrypt sector?"

        logger.info(f"Starting decryption test with config: '{conf_name}'")
        encrypt_data = conf["encrypt"]

        assert config.does_exist("output", conf["decrypt"])
        conf["decrypt"] = file_utils.clear_output_dir(
            output_dir, conf["decrypt"], logger)

        core = Core(conf)
        if disk_mode:
            if disk_path is None:
                pytest.skip("Disk path must be provided when disk_mode=True")
            core.set_disk_mode(True)
            core.change_container_path(disk_path)

        if isinstance(encrypt_data, list):
            for i, encrypt_conf in enumerate(encrypt_data):
                logger.info(f"Processing encryption layer {i+1}")
                assert config.does_exist(
                    "directories", encrypt_conf), "Directories should be specified!"
                assert config.does_exist(
                    "files", encrypt_conf), "files should be specified!"
                assert config.does_exist(
                    "password", encrypt_conf), "password should be specified!"
                directories = encrypt_conf["directories"]
                files = encrypt_conf["files"]
                password = encrypt_conf["password"]
                # Generate additional passwords of the same length
                import random
                import string
                def generate_similar_password(length):
                    chars = string.ascii_letters + string.digits + string.punctuation
                    return ''.join(random.choice(chars) for _ in range(length))
                
                passwords = [password]  # Start with original password
                password_length = len(password)
                
                # Generate additional passwords
                for _ in range(password_count):
                    passwords.append(generate_similar_password(password_length))

                logger.info("Calculating file hashes for verification...")
                layer_hash = hash_utils.get_all_files_hashes(
                    directories, files, use_full_paths=False)

                # Try each password
                for test_password in passwords:
                    # Clear and recreate output directory before each test
                    file_utils.clear_output_dir(output_dir, conf["decrypt"], logger)
                    
                    logger.info(f"Performing encryption with password: '{test_password}'")
                    encrypt_conf["password"] = test_password
                    core.encrypt_archive(encrypt_conf)
                    logger.info(f"Attempting decryption with password: '{test_password}'")
                    core.decrypt_archive(output_dir, test_password)

                    output_hash = hash_utils.get_all_files_hashes(
                        [output_dir], "", use_full_paths=False)

                    for new_path in output_hash.keys():
                        old_path = new_path.replace(output_dir, "")
                        if old_path in layer_hash:
                            old_hash = layer_hash[old_path]
                            new_hash = output_hash[new_path]
                            logger.info(f"Verifying hash integrity: '{old_path}'")
                            not_eq_msg = f"Hash mismatch - Original: {old_path}({old_hash}) != Decrypted: {new_path}({new_hash})"
                            assert layer_hash[old_path] == output_hash[new_path], not_eq_msg
                            logger.info("Hash verification successful")
                    file_utils.clear_output_dir(output_dir, conf["decrypt"], logger)