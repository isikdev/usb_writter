import os
from modules import config


def get_confs(conf_paths):
    configs = []

    for conf_path in conf_paths:
        _, file_extension = os.path.splitext(conf_path)
        if file_extension == ".json":
            config_data = config.parse_json(conf_path)
            conf_obj = (conf_path, config_data)
            configs.append(conf_obj)
        elif file_extension == ".txt":
            config_data = config.parse_note(conf_path)
            conf_obj = (conf_path, config_data)
            configs.append(conf_obj)
        else:
            print(f"invalid extension for config '{file_extension}'")

    return configs
