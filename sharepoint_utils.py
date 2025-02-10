from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import os
from dotenv import load_dotenv
import json
from concurrent.futures import ThreadPoolExecutor
from version_control import calcular_hash, registrar_novedades, cargar_historial, guardar_historial

load_dotenv(".env")

SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
FOLDER_URL = os.getenv("SHAREPOINT_FOLDER_URL")
USERNAME = os.getenv("SHAREPOINT_USERNAME")
PASSWORD = os.getenv("SHAREPOINT_PASSWORD")

def conectar_sharepoint():
    try:
        credentials = UserCredential(USERNAME, PASSWORD)
        ctx = ClientContext(SITE_URL).with_credentials(credentials)
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        print(f"✅ Conectado a SharePoint: {web.properties['Title']}")
        return ctx
    except Exception as e:
        print(f"❌ Error de conexión a SharePoint: {e}")
        return None

def obtener_archivos_sharepoint():
    ctx = conectar_sharepoint()
    if not ctx:
        raise HTTPException(status_code=500, detail="Error de conexión a SharePoint")

    folder = ctx.web.get_folder_by_server_relative_url(FOLDER_URL)
    files = folder.files
    ctx.load(files)
    ctx.execute_query()

    historial = cargar_historial()
    nuevo_historial = {}
    archivos = []
    cambios_detectados = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        resultados = list(executor.map(lambda f: procesar_archivo(f, ctx, historial), files))

    archivos = [r for r in resultados if r]
    for archivo in archivos:
        nombre_archivo = archivo["nombre"]
        if nombre_archivo in historial and historial[nombre_archivo]["hash"] != archivo["hash"]:
            cambios_detectados.append({
                "tipo": "Modificado",
                "nombre": nombre_archivo,
                "fecha_anterior": historial[nombre_archivo]["fecha_modificacion"],
                "fecha_nueva": archivo["fecha_modificacion"],
                "hash_anterior": historial[nombre_archivo]["hash"],
                "hash_nuevo": archivo["hash"]
            })
        elif nombre_archivo not in historial:
            cambios_detectados.append({
                "tipo": "Nuevo",
                "nombre": nombre_archivo,
                "fecha_creacion": archivo["fecha_creacion"]
            })

        nuevo_historial[nombre_archivo] = archivo

    guardar_historial(nuevo_historial)
    registrar_novedades(cambios_detectados)

    return archivos, cambios_detectados

def procesar_archivo(file, ctx, historial):
    try:
        server_relative_url = file.serverRelativeUrl
        enlace = f"{SITE_URL}{server_relative_url}".replace(" ", "%20")
        fecha_modificacion = str(file.time_last_modified)
        fecha_creacion = str(file.time_created)
        tamano_archivo = round(file.length / 1024, 2)

        try:
            archivo = ctx.web.get_file_by_server_relative_url(server_relative_url)
            contenido_binario = archivo.open_binary(ctx).content
            hash_actual = calcular_hash(contenido_binario)
            estado = "Válido"
        except:
            hash_actual = "ERROR"
            estado = "Error en lectura"

        return {
            "nombre": file.name,
            "tipo": file.name.split(".")[-1].upper(),
            "enlace": enlace,
            "fecha_creacion": fecha_creacion,
            "fecha_modificacion": fecha_modificacion,
            "tamano_kb": tamano_archivo,
            "hash": hash_actual,
            "estado": estado
        }
    except Exception as e:
        print(f"⚠️ Error al procesar {file.name}: {e}")
        return None
