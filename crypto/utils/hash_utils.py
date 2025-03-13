import hashlib
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def calculate_file_hash(file_path, hash_algorithm='sha256'):
    hash_func = hashlib.new(hash_algorithm)

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()


def get_all_files_hashes(directories, files, hash_algorithm='sha256', use_full_paths=False):
    import file_utils
    file_hashes = {}

    for dir in directories:
        dir_files = file_utils.get_all_files(dir)
        for file_path in dir_files:
            file_hash = calculate_file_hash(file_path, hash_algorithm)
            file_hashes[file_path] = file_hash

    if files != "":
        for file_path in files:
            file_hash = calculate_file_hash(file_path, hash_algorithm)
            if use_full_paths:
                file_hashes[file_path] = file_hash
            else:
                file_hashes[os.path.basename(file_path)] = file_hash

    return file_hashes
