class Msg:
    class Info:
        archiving_container = "Attempting to archive the container..."
        archive_validated = "Archive validated."
        deleting_old_par2 = "Deleting old PAR2 files..."

        @staticmethod
        def gpt_save_file_not_exists(gpt_save_file: str) -> str:
            return f"File {gpt_save_file} does not exist. Skip gpt verification."

        @staticmethod
        def partition_save_file_not_exists(partition_save_file: str) -> str:
            return f"File {partition_save_file} does not exist. Skip partition verification."

        @staticmethod
        def deleted_old_par2(old_par2: str) -> str:
            return f"Deleted {old_par2}"

        @staticmethod
        def added_directory(directory: str) -> str:
            return f"The Directory {directory} has been successfully added to the archive."

        @staticmethod
        def extracted_directory(directory: str) -> str:
            return f"The Directory {directory} has been successfully extracted."

        @staticmethod
        def added_file(file_path: str) -> str:
            return f"File {file_path} added to the disk."

        @staticmethod
        def file_added_to_archive(file_path: str) -> str:
            return f"File {file_path} added to the archive."

        @staticmethod
        def file_extracted(file: str) -> str:
            return f"The file {file} has been successfully extracted."

        @staticmethod
        def first_archive_path_not_found(first_archive_path: str) -> str:
            return f"File not found: {first_archive_path}"

        extracting_cont_from_rar = "Attempting to extract container from archive..."
        extracted_cont_from_rar = "Container has been successfully extracted!"
        starting_encrypting_files = "Starting file encryption..."
        starting_decrypting_files = "Starting file decryption..."
        extracting_archive = "Extracting the archive..."
        validating_archive = "Validating archive..."
        verifying_archive = "Verifying the archive..."

        @staticmethod
        def object_validated(check_object: str) -> str:
            return f"{check_object} validated."

        @staticmethod
        def removing_container(container_path: str) -> str:
            return f"Removing container {container_path}"

    class Warn:
        container_doesnt_exist = "Container file does not exist."
        wrong_params = "Incorrect parameters."
        critical_value_not_found = "Critical value for par2disk is not found in config, impossible to continue."


        @staticmethod
        def archive_integrity_check_failed(offending_file: str) -> str:
            return f"Archive integrity check failed. The offending file '{offending_file}'"

        @staticmethod
        def invalid_priority(priority: int, os: str) -> str:
            return f"Invalid priority '{priority}' for {os}."

        @staticmethod
        def item_not_specified(item: str, default_item: str) -> str:
            return f"{item} is not specified, using default: [{default_item}]"

        @staticmethod
        def object_doesnt_exist(obj: str) -> str:
            return f"Configuration for {obj} is missing."

        @staticmethod
        def object_not_validated(check_object: str) -> str:
            return f"Integrity check failed for {check_object}."

        @staticmethod
        def old_and_new_hash(old_hashsum: str, new_hashsum: str) -> str:
            return f"Old hash: {old_hashsum}; New hash: {new_hashsum}"

        @staticmethod
        def unknown_option(key: str, value: str) -> str:
            return f"Unknown option '{key}: {value}'"

        @staticmethod
        def unknown_sector(sector: str) -> str:
            return f"Unknown sector '{sector}'"

        @staticmethod
        def extra_dir_is_not_dir(extra_dir: str) -> str:
            return f"Extra directory '{extra_dir}' is not a directory"

    class Err:
        bad_rarfile = "Error: Incorrect password or corrupted archive."
        cant_get_disk_size = "Could not retrieve disk size."
        invalid_size_string_format = "Invalid size string format."
        linux_drive_not_supported = "Device operations are only supported on Windows."
        rarfile_wrongpas = "Error: Incorrect password."
        wrong_pass = "Incorrect password."

        @staticmethod
        def adding_file_error(file_path: str, error: Exception) -> str:
            return f"Error adding file {file_path}: {error}"

        @staticmethod
        def reading_archive_error(error: Exception) -> str:
            return f"Error reading archive: {error}"

        @staticmethod
        def adding_file_to_archive_error(file_path: str, error: Exception) -> str:
            return f"Error adding file {file_path} to archive: {error}"
        
        @staticmethod
        def adding_directory_to_archive_error(dir_path: str, error: Exception) -> str:
            return f"Error adding directory {dir_path} to archive: {error}"
        
        @staticmethod
        def extracting_directory_error(error: Exception) -> str:
            return f"Error extracting directory: {error}"

        @staticmethod
        def cant_read_file(file_path: str) -> str:
            return f"Error: Could not read file - {file_path}"

        @staticmethod
        def disk_size_not_dividing_by_buffer(size: int, buffer_size: int) -> str:
            return f"Disk size ({size} bytes) is not divisible by buffer size ({buffer_size} bytes)"

        @staticmethod
        def file_not_found(file_path: str) -> str:
            return f"Error: File not found - {file_path}"

        @staticmethod
        def processing_archive_error(error: Exception) -> str:
            return f"Error processing archive: {error}"

        @staticmethod
        def unknown_unit(unit: str) -> str:
            return f"Unknown unit: {unit}"

        @staticmethod
        def unrar_cont_error(error: Exception) -> str:
            return f"Error: {error}"

        @staticmethod
        def writing_to_disk_error(error: Exception) -> str:
            return f"Error writing to disk: {error}"

        @staticmethod
        def parity_created_with_dif_recovery_percent(recovery_percent: int, stored_recovery: int) -> str:
            return f"Parity file was created with {stored_recovery}% recovery,\n" \
                   f"but handler is configured for {recovery_percent}%\n" \
                   f"Try deleting the parity file and try again."
        
        @staticmethod
        def parity_created_with_dif_buffer_size(buffer_size: int, stored_buffer_size: int) -> str:
            return f"Parity file was created with {stored_buffer_size} buffer size,\n" \
                   f"but handler is configured for {buffer_size} buffer size\n" \
                   f"Try deleting the parity file and try again."


    class PBar:
        adding_to_archive = "Adding to archive"
        decrypting_part = "Decrypting"
        encrypting_part = "Encrypting"
        extracting_file = "Extracting files"
        fetching_container_hash = "Fetching container hash"
        filling_container_with_noise = "Filling container with noise"
        loading_archive = "Loading the archive"
        uploading_archive_to_disk = "Uploading files to disk"


class Def_val:
    # Default values
    container_path = "container.crypt"
    new_container_size = "1G"
    block_size = "10M"
    buffer_size = "4M"
    noize = True
    cpu_priority = "normal"
    split_mode = False
    min_chunk_ratio = 0.7

    class Par2disk:
        physic_number = None
        recovery_percent: int = 20 
        gpt_save_file: str = "save_gpt"
        partition_save_file: str = "save_part"
        make_check: bool = False
