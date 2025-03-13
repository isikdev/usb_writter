import subprocess


def make_par2(file_path, parfile_name, recovety_procent):
    command = [
        "par2", "create",
        f"-r{recovety_procent}",
        parfile_name,
        file_path
    ]

    print(command)
    result = subprocess.run(command)
    if result.returncode != 0:
        return False
    return True


def repair_files(parfile_name):
    command = [
        "par2", "repair",
        parfile_name
    ]

    result = subprocess.run(command)
    if result.returncode != 0:
        return False
    return True


def verify_files(parfile_name):
    command = [
        "par2", "verify",
        parfile_name
    ]

    result = subprocess.run(command)
    if result.returncode != 0:
        return repair_files(parfile_name)
    return True
