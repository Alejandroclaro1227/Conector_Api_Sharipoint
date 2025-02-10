import json
import os
from config import HISTORIAL_ARCHIVOS

# 🔹 Cargar historial desde JSON
def cargar_historial():
    if os.path.exists(HISTORIAL_ARCHIVOS):
        with open(HISTORIAL_ARCHIVOS, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 🔹 Guardar historial actualizado en JSON
def guardar_historial(historial):
    with open(HISTORIAL_ARCHIVOS, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4, ensure_ascii=False)
