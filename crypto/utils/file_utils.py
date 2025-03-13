import os
import shutil


def get_all_files(directory):
    files = []

    for root, dirs, files_list in os.walk(directory):
        for file in files_list:
            files.append(os.path.join(root, file))

    return files


def get_files_from_dir(dir):
    try:
        files = [
            f
            for f in os.scandir(dir)
            if f.is_file()
        ]
        if not files:
            return None
        return files
    except (FileNotFoundError, NotADirectoryError, OSError) as e:
        print(f"Error accessing directory: {e}")
        return None


def clear_output_dir(output_dir, decrypt_data, logger):
    # assert config.does_exist("output", decrypt_data)

    try:
        if decrypt_data["output"] != output_dir:

            logger.warning(
                f"The output directory was not specified in the configuration file.  It has been set to '{output_dir}' for testing.")
            decrypt_data["output"] = output_dir

            if not os.path.exists(output_dir):
                logger.info(f"Couldn't find '{
                            output_dir}' dir, creating...")
                os.mkdir(output_dir)

        logger.info(f"Remove all in '{output_dir}'")
        shutil.rmtree(output_dir)
        logger.info(f"Recreating '{output_dir}' directory")
        os.makedirs(output_dir)
    except Exception as e:
        logger.error(e)
    finally:
        return decrypt_data
