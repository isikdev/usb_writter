import logging
import sys

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Экспортируем логгер для использования в других модулях
logger = logging.getLogger('crypto') 