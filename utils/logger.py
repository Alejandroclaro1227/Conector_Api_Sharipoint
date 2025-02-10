import logging
from config import config

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("SegundoConector")
    logger.setLevel(config.LOG_LEVEL)
    
    # Crear handlers
    file_handler = logging.FileHandler(config.LOG_PATH)
    console_handler = logging.StreamHandler()
    
    # Crear formato
    formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Agregar handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 