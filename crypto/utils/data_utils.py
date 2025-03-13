import re
from modules.wrapers import logging as log
from modules.config import Msg


def parse_size(size_str: str) -> int:
    size_units = {
        'b': 1,
        'k': 1024,
        'm': 1024**2,
        'g': 1024**3,
        't': 1024**4,
    }

    match = re.match(r'(\d+)([a-zA-Z]+)', size_str.strip())
    if not match:
        log.logging.error(Msg.Err.invalid_size_string_format)
        raise ValueError(Msg.Err.invalid_size_string_format)

    size = int(match.group(1))
    unit = match.group(2).lower()

    if unit not in size_units:
        log.logging.error(Msg.Err.unknown_unit(unit))
        raise ValueError(Msg.Err.unknown_unit(unit))

    return size * size_units[unit]
