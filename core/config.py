from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Control de Versiones API"
    APP_VERSION: str = "6.0"
    DEBUG: bool = False
    
    # AWS Settings
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str
    
    # API Settings
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8300
    
    # Paths
    EXCEL_PATH: str = "Documentos_SharePoint.xlsx"
    HISTORIAL_PATH: str = "data/historial_archivos.json"
    
    # SharePoint Settings
    SHAREPOINT_SITE_URL: str
    SHAREPOINT_FOLDER_URL: str
    SHAREPOINT_USERNAME: str
    SHAREPOINT_PASSWORD: str
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 