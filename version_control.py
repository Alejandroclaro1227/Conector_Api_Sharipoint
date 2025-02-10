import os
import json
import hashlib

HISTORIAL_ARCHIVOS = "data/historial_archivos.json"
NOVEDADES_REGISTRO = "data/novedades.json"

# 🔹 Verifica si el directorio 'data/' existe, si no, lo crea
if not os.path.exists("data"):
    os.makedirs("data")

def calcular_hash(contenido_binario):
    hasher = hashlib.sha256()
    hasher.update(contenido_binario)
    return hasher.hexdigest()

def cargar_historial():
    if not os.path.exists(HISTORIAL_ARCHIVOS):
        return {}  # Si el archivo no existe, retorna un historial vacío
    with open(HISTORIAL_ARCHIVOS, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_historial(historial):
    if not os.path.exists("data"):
        os.makedirs("data")  # 🔹 Crea el directorio si no existe
    with open(HISTORIAL_ARCHIVOS, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4, ensure_ascii=False)

def cargar_novedades():
    if not os.path.exists(NOVEDADES_REGISTRO):
        return []  # Si no hay novedades registradas, retorna una lista vacía
    with open(NOVEDADES_REGISTRO, "r", encoding="utf-8") as f:
        return json.load(f)

def registrar_novedades(novedades):
    if not os.path.exists("data"):
        os.makedirs("data")  # 🔹 Crea el directorio si no existe
    log_novedades = cargar_novedades()
    log_novedades.extend(novedades)
    with open(NOVEDADES_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(log_novedades, f, indent=4, ensure_ascii=False)
