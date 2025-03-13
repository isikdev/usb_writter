import pytest
from modules import aes
from modules import winDiskHandler
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def test_configs_translation(configs_paths):
    txt_confs, json_confs = configs_paths

    assert txt_confs is not None
    assert json_confs is not None

    logger.info("Checking configurations for equality...")
    for json_conf, txt_conf in zip(json_confs, txt_confs):
        assert json_conf[1] == txt_conf[1]
