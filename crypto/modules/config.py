import json
from .wrapers.logging import logging
from .constants import Def_val
from .constants import Msg


def parse_json(json_path: str):
    with open(json_path, 'r') as js_file:
        data = json.load(js_file)

    return data


def parse_note(note_path: str):
    dict_keys = {
        # base config
        "шаг": "block_size",
        "путь": "container_path",
        "экстра": "extra",
        "размер": "new_container_size",
        "режим": "mode",
        "приоритет": "cpu_priority",
        "буффер": "buffer_size",
        "шум": "noize",

        # encrypt
        "ши": "encrypt",
        "файлы": "files",
        "папки": "directories",

        # decrypt
        "де": "decrypt",
        "вывод": "output",

        # rar
        "рар": "rar",
        "рпуть": "archive_path",
        "кусок": "piece_size",

        # unrar
        "урар": "unrar",
        "упуть": "first_archive_path",

        # par2deep
        "пар2": "par2",
        "ппуть": "file_path",
        "парпуть": "par2file_path",

        # par2disk
        "пар2драйв": "par2disk",
        "физикномер": "physic_number",
        "гптс": "gpt_save_file",
        "разделс": "partition_save_file",
        "проверка": "make_check",

        # others
        "пар": "password",
        "очистка": "clean",
        "процент": "recovery_percent",
        "хуш": "hashsum_limit",
    }

    value_dict = {
        "ши": "encrypt",
        "де": "decrypt",
        "рар": "rar",
        "очнизко": "idle",
        "низк": "low",
        "норм": "normal",
        "выск": "high",
        "очвыск": "very high",
        "реалтайм": "realtime",
        "-": False,
        "+": True,
        "_": ""
    }

    sectors = [
        "encrypt",
        "decrypt",
        "rar",
        "unrar",
        "par2",
        "par2disk"
    ]

    list_value = [
        "directories",
        "files"
    ]

    def parse_line(line: str):
        parts = line.split(" ", 1)
        key = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        if rest.startswith("(") and rest.endswith(")"):
            value, comment = rest[1:-1], ""
        else:
            value_comment_parts = rest.split(" ", 1)
            value = value_comment_parts[0]
            comment = value_comment_parts[1] if len(
                value_comment_parts) > 1 else ""
        return key, value

    def process_value(value: str):
        if not value:
            return
        elif value in value_dict:
            return value_dict[value]
        elif "," in value:
            list_val = []
            for val in value.split(","):
                list_val.append(process_value(val))
            return list_val
        else:
            return value

    config = {}
    lines = []
    try:
        with open(note_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(Msg.Err.file_not_found(note_path))
    except IOError:
        print(Msg.Err.cant_read_file(note_path))
    lines = [line.strip() for line in lines if line.strip()]

    current_sector = "", {}
    encrypt_conf = {}

    def isSector(line):
        return " " not in line

    def isOption(line):
        return " " in line

    for line in lines:
        if line.strip()[0] == "#":
            continue
        if isSector(line):
            if line not in dict_keys:
                logging.warning(Msg.Warn.unknown_sector(line))
                continue
            if current_sector[0] != "" and current_sector[0] != "encrypt":
                config[current_sector[0]] = current_sector[1]
                current_sector = dict_keys[line], {}
            elif current_sector[0] == "encrypt":
                enc_sec = current_sector[0]
                if enc_sec not in config:
                    config[enc_sec] = []
                config[enc_sec].append(encrypt_conf.copy())
                current_sector = dict_keys[line], {}
            else:
                current_sector = dict_keys[line], {}
        elif isOption(line):
            key, value = parse_line(line)
            if key not in dict_keys and value not in dict_keys:
                logging.warning(Msg.Warn.unknown_option(key, value))
                continue
            valid_key = dict_keys[key]
            valid_value = process_value(value)

            def notListButMustBe():
                return valid_key in list_value and not isinstance(valid_value, list)

            if notListButMustBe():
                valid_value = [valid_value]

            if current_sector[0] == "":
                config[valid_key] = valid_value
            elif current_sector[0] == "encrypt":
                encrypt_conf[valid_key] = valid_value
            else:
                current_sector[1][valid_key] = valid_value

    # finalize
    config[current_sector[0]] = current_sector[1]

    return config


def parse_data(file_path: str):
    def is_json_file():
        return file_path.endswith('.json')

    if is_json_file():
        return parse_json(file_path)
    else:
        return parse_note(file_path)


def process_rar_data(rar_data):
    result = {
        "archive_path": "archive",
        "piece_size": "50m",
        "recovery_procent": "3"
    }

    for item in result:
        if item not in rar_data:
            logging.warning(Msg.Warn.item_not_specified(item, result[item]))
        else:
            result[item] = rar_data[item]
    return result


def process_unrar_data(unrar_data):
    result = {
        "first_archive_path": "archive.part1.rar",
        "output": "."
    }

    for item in result:
        if item not in unrar_data:
            logging.warning(Msg.Warn.item_not_specified(item, result[item]))
        else:
            result[item] = unrar_data[item]
    if "password" in unrar_data:
        result["password"] = unrar_data["password"]
    return result

def process_par2disk_data(par2disk_data) -> tuple[dict, bool]:
    critical_keys = ["physic_number"]
    result = {
        "physic_number": Def_val.Par2disk.physic_number,
        "gpt_save_file": Def_val.Par2disk.gpt_save_file,
        "partition_save_file": Def_val.Par2disk.partition_save_file,
        "recovery_percent": Def_val.Par2disk.recovery_percent,
        "make_check": Def_val.Par2disk.make_check
    }

    can_continue = True
    for item in result:
        if item not in par2disk_data:
            if item in critical_keys:
                can_continue = False
            logging.warning(Msg.Warn.item_not_specified(item, result[item]))
        else:
            result[item] = par2disk_data[item]
    return result, can_continue


def get_extradir(encrypt_data) -> str:
    if "extra" not in encrypt_data:
        return ""
    else:
        return encrypt_data["extra"]


def check_mode(data) -> str | None:
    if "mode" not in data:
        return None
    else:

        return ''.join(data["mode"])


def does_exist(obj, data) -> bool:
    if obj not in data:
        logging.warning(Msg.Warn.object_doesnt_exist(obj))
        return False
    return True
