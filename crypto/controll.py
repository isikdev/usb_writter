import os
import sys
import psutil
import platform
from crypto.controllers.orchestrate import pipeline
from crypto.wrappers.logging import logging
from crypto.constants import Msg, Def_val

# Значения по умолчанию
noize = Def_val.noize
cpu_priority = Def_val.cpu_priority


def get_user_input(prompt: str, default):
    """
    Получает ввод пользователя с значением по умолчанию
    
    Args:
        prompt: Приглашение для ввода
        default: Значение по умолчанию
        
    Returns:
        str: Введенное пользователем значение или значение по умолчанию
    """
    user_input = input(f"{prompt} [{default}]: ")
    return user_input.strip() or default


def handle_priority_linux(priority):
    """
    Устанавливает приоритет процесса для Linux
    
    Args:
        priority: Приоритет процесса
    """
    process = psutil.Process()
    if priority == "idle":
        process.ionice(psutil.IOPRIO_CLASS_RT, value=7)
    elif priority == "low":
        process.ionice(psutil.IOPRIO_CLASS_RT, value=6)
    elif priority == "normal":
        process.ionice(psutil.IOPRIO_CLASS_RT, value=5)
    elif priority == "high":
        process.ionice(psutil.IOPRIO_CLASS_RT, value=4)
    elif priority == "realtime":
        process.ionice(psutil.IOPRIO_CLASS_RT, value=0)
    else:
        logging.warning(Msg.Warn.invalid_priority(priority, "Linux"))


def handle_priority_windows(priority):
    """
    Устанавливает приоритет процесса для Windows
    
    Args:
        priority: Приоритет процесса
    """
    import win32process
    import win32api
    import win32con
    
    process = psutil.Process()
    if priority == "idle":
        win32process.SetPriorityClass(
            win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, process.pid),
            win32process.IDLE_PRIORITY_CLASS)
    elif priority == "low":
        win32process.SetPriorityClass(
            win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, process.pid),
            win32process.BELOW_NORMAL_PRIORITY_CLASS)
    elif priority == "normal":
        win32process.SetPriorityClass(
            win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, process.pid),
            win32process.NORMAL_PRIORITY_CLASS)
    elif priority == "high":
        win32process.SetPriorityClass(
            win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, process.pid),
            win32process.ABOVE_NORMAL_PRIORITY_CLASS)
    elif priority == "realtime":
        win32process.SetPriorityClass(
            win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, process.pid),
            win32process.REALTIME_PRIORITY_CLASS)
    else:
        logging.warning(Msg.Warn.invalid_priority(priority, "Windows"))


def handle_priority(priority):
    """
    Устанавливает приоритет процесса в зависимости от операционной системы
    
    Args:
        priority: Приоритет процесса
    """
    if platform.system() == "Windows":
        handle_priority_windows(priority)
    else:
        handle_priority_linux(priority)


def main():
    """
    Основная функция программы
    """
    # Получаем путь к конфигурационному файлу из аргументов командной строки
    if len(sys.argv) < 2:
        print("Использование: python controll.py <путь_к_конфигу>")
        return
        
    config_path = sys.argv[1]
    
    # Импортируем модуль config только здесь, чтобы избежать циклических импортов
    from modules import config
    
    # Загружаем конфигурацию
    data = config.load_config(config_path)
    
    # Устанавливаем приоритет процесса
    if "cpu_priority" in data:
        handle_priority(data["cpu_priority"])
    else:
        handle_priority(cpu_priority)
    
    # Запускаем основной конвейер обработки
    pipeline(data)


if __name__ == "__main__":
    main()
