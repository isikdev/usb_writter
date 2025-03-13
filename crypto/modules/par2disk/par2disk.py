from typing import List
from .. import config
from ..wrapers.logging import logging as log
from ..constants import Msg, Def_val
from .gpt import GPTHandler
from .partition import PartitionHandler
from ..winDiskHandler import DiskHandler
import os
from functools import wraps

def check_can_continue(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.can_continue:
            log.warning(Msg.Warn.critical_value_not_found)
            return None
        return func(self, *args, **kwargs)
    return wrapper

class Par2Disk:
    gpt_save_extension = ".gpt"
    partition_save_extension = ".part"
    make_check = Def_val.Par2disk.make_check

    def __init__(self, par2disk_conf, disk_letter: str, buffer_size: int) -> None:
        if par2disk_conf is not None:
            self.par2disk_conf, self.can_continue = config.process_par2disk_data(par2disk_conf)
        else :
            self.can_continue = False
        if not self.can_continue:
            return

        self.make_check = self.par2disk_conf["make_check"]
        self.disk_letter = disk_letter
        self.buffer_size = buffer_size
        self.disk_path = f"\\\\.\\PhysicalDrive{self.par2disk_conf["physic_number"]}"
        self.gpt_handler = GPTHandler(self.disk_path)
        self.gpt_save_file = self.par2disk_conf["gpt_save_file"] + self.gpt_save_extension
        self.partition_save_file = self.par2disk_conf["partition_save_file"] + self.partition_save_extension
        self.partition_handler = PartitionHandler(self.disk_letter, int(self.par2disk_conf["recovery_percent"]), self.buffer_size)
    
    @check_can_continue
    def get_disk_info(self):
        return self.gpt_handler.get_disk_info()
    
    @check_can_continue
    def display_disk_info(self):
        disk_info = self.get_disk_info()
        print(f"Disk Information:")
        for key, value in disk_info.items():
            print(f"{key}: {value}")
    
    @check_can_continue
    def create_parity_gpt(self) -> None:
        if os.path.exists(self.gpt_save_file):
            os.remove(self.gpt_save_file)
        self.gpt_handler.save_gpt_header(self.gpt_save_file)
    
    @check_can_continue
    def create_parity_partition(self) -> None:
        if os.path.exists(self.partition_save_file):
            os.remove(self.partition_save_file)
        self.partition_handler.create_parity(self.partition_save_file)

    @check_can_continue
    def verify_and_repair_gpt(self) -> None:
        if not os.path.exists(self.gpt_save_file):
            log.info(Msg.Info.gpt_save_file_not_exists(self.gpt_save_file))
            return
        if not self.gpt_handler.verify_gpt_header(self.gpt_save_file):
            self.gpt_handler.restore_gpt_header(self.gpt_save_file)
    
    @check_can_continue
    def verify_and_repair_partition(self) -> None:
        if not os.path.exists(self.partition_save_file):
            log.info(Msg.Info.partition_save_file_not_exists(self.partition_save_file))
            return
        self.partition_handler.verify_and_repair(self.partition_save_file)

    @check_can_continue
    def create_disk_parity(self) -> None:
        self.create_parity_gpt()
        self.create_parity_partition()
    
    @check_can_continue
    def verify_and_repair_disk(self) -> None:
        if self.make_check:
            self.verify_and_repair_gpt()
            self.verify_and_repair_partition()
