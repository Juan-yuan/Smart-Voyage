import logging
import os
import sys

project_directory = os.path.dirname(os.path.abspath(__file__))
if project_directory not in sys.path:
    sys.path.insert(0, project_directory)

from config import Config


def _resolve_log_file(log_file):
    """Return a log path inside this project directory."""
    if not log_file:
        return os.path.join(project_directory, 'logs', 'app.log')
    if not os.path.isabs(log_file):
        return os.path.join(project_directory, log_file)
    configured_root = os.path.basename(os.path.dirname(os.path.dirname(os.path.normpath(log_file))))
    if configured_root != os.path.basename(project_directory):
        return os.path.join(project_directory, 'logs', os.path.basename(log_file))
    return log_file


def setup_logger(name, log_file='logs/app.log'):
    log_file = _resolve_log_file(log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = logging.Formatter('%(name)s - %(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler(filename=log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


log_file = _resolve_log_file(Config().log_file)
logger = setup_logger('SmartVoyage', log_file)

if __name__ == '__main__':
    for handler in logger.handlers:
        handler.flush()
