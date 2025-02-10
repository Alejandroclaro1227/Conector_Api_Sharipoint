import os
from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass
from typing import Dict

# 🔹 Cargar variables de entorno
load_dotenv(".env")

# 🔹 Configuración de SharePoint
SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
FOLDER_URL = os.getenv("SHAREPOINT_FOLDER_URL")
USERNAME = os.getenv("SHAREPOINT_USERNAME")
PASSWORD = os.getenv("SHAREPOINT_PASSWORD")

# 🔹 Estructura de carpetas
FOLDERS = {
    "data": {
        "logs": "data/logs",
        "cache": "data/cache",
        "history": "data/history",
        "temp": "data/temp"
    },
    "documents": {
        "academic": "documents/academic",
        "administrative": "documents/administrative", 
        "student": "documents/student",
        "faculty": "documents/faculty",
        "general": "documents/general"
    },
    "config": "config",
    "utils": "utils"
}

# 🔹 Rutas de archivos
PATHS = {
    "historial": "data/history/historial_archivos.json",
    "novedades": "data/history/novedades.json",
    "logs": "data/logs/app.log",
    "cache": "data/cache/sharepoint_cache.json",
    "excel": "documents/general/Documentos_SharePoint.xlsx"
}

@dataclass
class AppConfig:
    # Rutas
    BASE_DIR: Path = Path(__file__).parent
    EXCEL_PATH: Path = BASE_DIR / "Documentos_SharePoint.xlsx"
    HISTORIAL_PATH: Path = BASE_DIR / "data" / "historial_archivos.json"
    LOG_PATH: Path = BASE_DIR / "logs" / "app.log"

    # Intervalos
    SYNC_INTERVAL: int = 300  # 5 minutos en segundos

    # Estados
    ESTADO_NUEVO: str = "Nuevo"
    ESTADO_MODIFICADO: str = "Modificado"
    ESTADO_VALIDO: str = "Válido"

    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8300
    API_TITLE: str = "API de Control de Versiones desde Excel"
    API_DESCRIPTION: str = "Monitorea archivos desde un Excel y detecta cambios"
    API_VERSION: str = "6.0"

    # Logging
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_LEVEL: str = "INFO"

    def __post_init__(self):
        # Crear directorios necesarios
        self.BASE_DIR.mkdir(exist_ok=True)
        self.HISTORIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

config = AppConfig()
