import pandas as pd
import json
from typing import Dict
import logging

from config import config

logger = logging.getLogger(__name__)

class ArchivoRepository:
    def leer_excel(self) -> pd.DataFrame:
        try:
            df = pd.read_excel(config.EXCEL_PATH)
            logger.info(f"Excel leído correctamente. {len(df)} registros encontrados")
            return df
        except Exception as e:
            logger.error(f"Error al leer el Excel: {e}")
            raise

    def cargar_historial(self) -> Dict:
        try:
            if config.HISTORIAL_PATH.exists():
                with open(config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error al cargar historial: {e}")
            return {}

    def guardar_historial(self, historial: Dict) -> None:
        try:
            with open(config.HISTORIAL_PATH, "w", encoding="utf-8") as f:
                json.dump(historial, f, indent=4, ensure_ascii=False)
            logger.info("Historial guardado correctamente")
        except Exception as e:
            logger.error(f"Error al guardar historial: {e}")
            raise 