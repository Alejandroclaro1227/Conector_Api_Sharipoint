import json
import os
from config import NOVEDADES_REGISTRO

# 🔹 Cargar novedades desde JSON
def cargar_novedades():
    if os.path.exists(NOVEDADES_REGISTRO):
        with open(NOVEDADES_REGISTRO, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# 🔹 Guardar novedades en JSON
def registrar_novedades(novedades):
    log_novedades = cargar_novedades()
    log_novedades.extend(novedades)
    with open(NOVEDADES_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(log_novedades, f, indent=4, ensure_ascii=False)
