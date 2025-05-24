import logging
import sys

logger = logging.getLogger("vk_photos")
logger.setLevel(logging.DEBUG)

# Форматтер по умолчанию
default_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Консоль — только ошибки
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(default_formatter)
logger.addHandler(console_handler)

# Для GUI: сюда можно будет подключить TextHandler
def get_default_formatter():
    return default_formatter