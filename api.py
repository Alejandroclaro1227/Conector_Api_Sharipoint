from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import pandas as pd
import os
import json
import logging
import hashlib
from threading import Thread
import time
from typing import List, Dict, Optional
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
import boto3
from botocore.exceptions import ClientError
import io
import traceback

# 🔹 Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)

# 🔹 Configuración
EXCEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "output", "Documentos_SharePoint.xlsx"
)

# Asegurarse de que el directorio output existe
os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)

# Corregir la definición de la ruta con barras invertidas correctas
EXCEL_PATH = EXCEL_PATH.replace("\\", "/")

HISTORIAL_FILE = "historial.json"
HISTORIAL_COMPLETO_FILE = "historial_completo.json"
SYNC_INTERVAL = 120  # 2 minutos

# 🔹 Constantes para estados
ESTADO_NUEVO = "NUEVO"
ESTADO_MODIFICADO = "MODIFICADO"
ESTADO_VALIDO = "VÁLIDO"

# 🔹 Configuración de AWS S3
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)
BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")


# 🔹 Modelos Pydantic
class FileInfo(BaseModel):
    nombre: str
    tipo: str
    enlace: str
    fecha_modificacion: str
    tamano_kb: float
    hash: str
    estado: str


class ChangeInfo(BaseModel):
    tipo: str
    nombre: str
    fecha_anterior: Optional[str]
    fecha_nueva: Optional[str]
    hash_anterior: Optional[str]
    hash_nuevo: Optional[str]


class SyncResponse(BaseModel):
    archivos: List[FileInfo]
    cambios_detectados: List[ChangeInfo]
    timestamp: str
    total_archivos: int
    tiempo_ejecucion: float


app = FastAPI(
    title="SharePoint File Monitor API",
    description="API para monitoreo de archivos SharePoint",
    version="2.0",
)

# 🔹 Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas las orígenes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

console = Console()

# 🔹 Configuración
COLUMNAS_EXCEL = {
    "nombre": "Nombre",
    "ruta": "Ruta",
    "url": "URL",
    "tipo_archivo": "Tipo Archivo",
    "fecha_creacion": "Fecha Creación",
    "fecha_modificacion": "Fecha Modificación",
    "tamano": "Tamaño (KB)",
    "categoria": "Categoría",
    "estado": "Estado",
}


# 🔹 Cargar historial de archivos
def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# 🔹 Guardar historial actualizado
def guardar_historial(historial):
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4, ensure_ascii=False)


# 🔹 Calcular hash de un archivo en base a sus datos
def calcular_hash(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()


# 🔹 Función para subir archivo a S3
def subir_archivo_a_s3(df):
    try:
        # Crear un buffer en memoria con el Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        # Generar nombre del archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"documentos/Documentos_SharePoint_{timestamp}.xlsx"

        # Subir a S3
        s3_client.upload_fileobj(excel_buffer, BUCKET_NAME, s3_key)

        logging.info(f"Archivo subido exitosamente a S3: {s3_key}")
        return s3_key
    except ClientError as e:
        logging.error(f"Error al subir archivo a S3: {e}")
        raise HTTPException(status_code=500, detail=f"Error al subir archivo a S3: {e}")


# 🔹 Obtener archivos desde el Excel
def obtener_archivos_desde_excel():
    try:
        if not os.path.exists(EXCEL_PATH):
            raise HTTPException(
                status_code=500, detail=f"Excel no encontrado: {EXCEL_PATH}"
            )

        df = pd.read_excel(EXCEL_PATH)
        archivos = []

        for _, row in df.iterrows():
            try:
                # Manejo seguro de valores
                tipo_archivo = str(row[COLUMNAS_EXCEL["tipo_archivo"]])
                if pd.isna(tipo_archivo) or tipo_archivo.strip() == "":
                    tipo_archivo = "N/A"

                archivo = {
                    "nombre": str(row[COLUMNAS_EXCEL["nombre"]]),
                    "ruta": str(row[COLUMNAS_EXCEL["ruta"]]),
                    "url": str(row[COLUMNAS_EXCEL["url"]]),
                    "tipo_archivo": tipo_archivo,
                    "fecha_creacion": str(row[COLUMNAS_EXCEL["fecha_creacion"]]),
                    "fecha_modificacion": str(
                        row[COLUMNAS_EXCEL["fecha_modificacion"]]
                    ),
                    "tamano_kb": (
                        float(row[COLUMNAS_EXCEL["tamano"]])
                        if not pd.isna(row[COLUMNAS_EXCEL["tamano"]])
                        else 0.0
                    ),
                    "categoria": str(row[COLUMNAS_EXCEL["categoria"]]),
                    "estado": str(row[COLUMNAS_EXCEL["estado"]]),
                }
                archivos.append(archivo)
            except Exception as e:
                logging.warning(f"Error procesando fila: {str(e)}")
                continue

        return archivos

    except Exception as e:
        logging.error(f"Error leyendo Excel: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 🔹 Sincronización automática
def sincronizacion_automatica():
    while True:
        print("🔄 Sincronizando archivos desde Excel...")
        obtener_archivos_desde_excel()
        print(
            f"✅ Sincronización completada. Esperando {SYNC_INTERVAL // 60} minutos..."
        )
        time.sleep(SYNC_INTERVAL)


# 🔹 Iniciar sincronización en un hilo separado
thread = Thread(target=sincronizacion_automatica, daemon=True)
thread.start()


# 🔹 Estructura para guardar historial completo
def guardar_historial_completo(datos):
    try:
        # Si el archivo existe, cargamos el historial anterior
        if os.path.exists(HISTORIAL_COMPLETO_FILE):
            with open(HISTORIAL_COMPLETO_FILE, "r", encoding="utf-8") as f:
                historial_completo = json.load(f)
        else:
            historial_completo = []

        # Agregamos el nuevo registro con timestamp
        nuevo_registro = {
            "fecha": datetime.now().isoformat(),
            "archivos": datos["archivos"],
            "cambios": datos["cambios_detectados"],
            "s3_key": datos.get("s3_key", None),
        }

        historial_completo.append(nuevo_registro)

        # Guardamos el historial actualizado
        with open(HISTORIAL_COMPLETO_FILE, "w", encoding="utf-8") as f:
            json.dump(historial_completo, f, indent=4, ensure_ascii=False)

        return True
    except Exception as e:
        logging.error(f"Error al guardar historial completo: {e}")
        return False


# 🔹 Nuevo endpoint para obtener historial completo
@app.get("/historial", summary="Obtener historial completo de cambios y archivos")
async def obtener_historial_completo():
    try:
        if os.path.exists(HISTORIAL_COMPLETO_FILE):
            with open(HISTORIAL_COMPLETO_FILE, "r", encoding="utf-8") as f:
                historial = json.load(f)

            # Agregamos estadísticas
            total_registros = len(historial)
            total_cambios = sum(len(registro["cambios"]) for registro in historial)
            ultimo_registro = historial[-1]["fecha"] if historial else "Sin registros"

            return JSONResponse(
                content={
                    "estadisticas": {
                        "total_registros": total_registros,
                        "total_cambios": total_cambios,
                        "ultima_actualizacion": ultimo_registro,
                    },
                    "historial": historial,
                },
                status_code=200,
            )
        else:
            return JSONResponse(
                content={
                    "estadisticas": {
                        "total_registros": 0,
                        "total_cambios": 0,
                        "ultima_actualizacion": "Sin registros",
                    },
                    "historial": [],
                },
                status_code=200,
            )
    except Exception as e:
        logging.error(f"Error al obtener historial completo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 🔹 Endpoint para ver los archivos
@app.get("/archivos", summary="Obtener lista de archivos con información completa")
async def obtener_archivos():
    try:
        if not os.path.exists(EXCEL_PATH):
            return {
                "estado": "error",
                "mensaje": "No se encontró el archivo Excel",
                "archivos": [],
            }

        df = pd.read_excel(EXCEL_PATH)
        archivos = df.to_dict("records")

        return {
            "estado": "success",
            "timestamp": datetime.now().isoformat(),
            "total_archivos": len(archivos),
            "archivos": archivos,
        }
    except Exception as e:
        logging.error(f"Error obteniendo archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/historico", summary="Obtener historial completo de cambios y archivos")
async def obtener_historico():
    try:
        if not os.path.exists(EXCEL_PATH):
            return {
                "estado": "success",
                "mensaje": "No hay datos históricos disponibles",
                "datos": [],
            }

        df = pd.read_excel(EXCEL_PATH)

        # Organizar datos históricos por fecha
        historico = {}

        for _, row in df.iterrows():
            fecha = pd.to_datetime(row["Fecha Modificación"]).strftime("%Y-%m-%d")

            if fecha not in historico:
                historico[fecha] = {
                    "archivos": [],
                    "total_archivos": 0,
                    "tipos_archivo": set(),
                    "tamano_total": 0,
                }

            historico[fecha]["archivos"].append(
                {
                    "nombre": row["Nombre"],
                    "tipo": row["Tipo Archivo"],
                    "url": row["URL"],
                    "tamano_kb": round(float(row["Tamaño (KB)"]), 2),
                    "estado": row["Estado"],
                }
            )

            historico[fecha]["tipos_archivo"].add(row["Tipo Archivo"])
            historico[fecha]["tamano_total"] += float(row["Tamaño (KB)"])
            historico[fecha]["total_archivos"] += 1

        # Convertir el histórico a formato de lista y ordenar por fecha
        historico_lista = []
        for fecha, datos in historico.items():
            historico_lista.append(
                {
                    "fecha": fecha,
                    "total_archivos": datos["total_archivos"],
                    "tipos_archivo": list(datos["tipos_archivo"]),
                    "tamano_total_kb": round(datos["tamano_total"], 2),
                    "archivos": datos["archivos"],
                }
            )

        # Ordenar por fecha descendente
        historico_lista.sort(key=lambda x: x["fecha"], reverse=True)

        return {
            "estado": "success",
            "timestamp": datetime.now().isoformat(),
            "total_registros": len(historico_lista),
            "historico": historico_lista,
        }

    except Exception as e:
        logging.error(f"Error obteniendo histórico: {str(e)}")
        return {"estado": "error", "mensaje": str(e), "historico": []}


@app.get("/cambios", summary="Ver historial de cambios y anomalías detectadas")
async def obtener_cambios():
    try:
        if not os.path.exists(EXCEL_PATH):
            return {
                "estado": "error",
                "mensaje": "No se encontró el archivo Excel",
                "cambios": []
            }

        df_actual = pd.read_excel(EXCEL_PATH)
        
        # Convertir y ordenar fechas
        df_actual['Fecha Modificación'] = pd.to_datetime(df_actual['Fecha Modificación'])
        df_actual['Fecha Creación'] = pd.to_datetime(df_actual['Fecha Creación'])
        df_actual = df_actual.sort_values('Fecha Modificación', ascending=False)

        # Análisis temporal
        ultima_actualizacion = df_actual['Fecha Modificación'].max()
        periodos = {
            "ultima_hora": ultima_actualizacion - pd.Timedelta(hours=1),
            "hoy": ultima_actualizacion - pd.Timedelta(days=1),
            "ultima_semana": ultima_actualizacion - pd.Timedelta(days=7),
            "ultimo_mes": ultima_actualizacion - pd.Timedelta(days=30)
        }

        cambios_por_periodo = {}
        for periodo, fecha_limite in periodos.items():
            df_periodo = df_actual[df_actual['Fecha Modificación'] > fecha_limite]
            cambios_por_periodo[periodo] = [{
                "nombre": row['Nombre'],
                "tipo": row['Tipo Archivo'],
                "url": row['URL'],
                "fecha_modificacion": row['Fecha Modificación'].strftime("%Y-%m-%d %H:%M:%S"),
                "tamano_kb": round(row['Tamaño (KB)'], 2),
                "categoria": row['Categoría'],
                "estado": row['Estado']
            } for _, row in df_periodo.iterrows()]

        # Análisis de duplicados con orden temporal
        duplicados = []
        df_duplicados = df_actual[df_actual.duplicated(subset=['Nombre'], keep=False)]
        for nombre in df_duplicados['Nombre'].unique():
            archivos_dup = df_actual[df_actual['Nombre'] == nombre].sort_values('Fecha Modificación', ascending=False)
            duplicados.append({
                "nombre": nombre,
                "cantidad": len(archivos_dup),
                "tipo": archivos_dup.iloc[0]['Tipo Archivo'],
                "ultima_modificacion": archivos_dup.iloc[0]['Fecha Modificación'].strftime("%Y-%m-%d %H:%M:%S"),
                "ubicaciones": [{
                    "ruta": row['Ruta'],
                    "url": row['URL'],
                    "fecha_modificacion": row['Fecha Modificación'].strftime("%Y-%m-%d %H:%M:%S"),
                    "tamano_kb": round(row['Tamaño (KB)'], 2),
                    "estado": row['Estado']
                } for _, row in archivos_dup.iterrows()]
            })
        
        # Ordenar duplicados por fecha más reciente
        duplicados.sort(key=lambda x: x['ultima_modificacion'], reverse=True)

        # Análisis por tipo con orden temporal
        tipos_archivo = {}
        for tipo in df_actual['Tipo Archivo'].unique():
            df_tipo = df_actual[df_actual['Tipo Archivo'] == tipo]
            tipos_archivo[tipo] = {
                "cantidad": len(df_tipo),
                "tamano_total_kb": round(df_tipo['Tamaño (KB)'].sum(), 2),
                "ultima_modificacion": df_tipo['Fecha Modificación'].max().strftime("%Y-%m-%d %H:%M:%S"),
                "archivos_recientes": [{
                    "nombre": row['Nombre'],
                    "url": row['URL'],
                    "fecha_modificacion": row['Fecha Modificación'].strftime("%Y-%m-%d %H:%M:%S"),
                    "tamano_kb": round(row['Tamaño (KB)'], 2)
                } for _, row in df_tipo.nlargest(5, 'Fecha Modificación').iterrows()]
            }

        # Resumen general actualizado
        resumen = {
            "ultima_actualizacion": ultima_actualizacion.strftime("%Y-%m-%d %H:%M:%S"),
            "archivos_ultima_hora": len(cambios_por_periodo["ultima_hora"]),
            "archivos_hoy": len(cambios_por_periodo["hoy"]),
            "archivos_ultima_semana": len(cambios_por_periodo["ultima_semana"]),
            "total_archivos": len(df_actual),
            "total_duplicados": len(duplicados),
            "tamano_total_kb": round(df_actual['Tamaño (KB)'].sum(), 2)
        }

        return {
            "estado": "success",
            "timestamp": datetime.now().isoformat(),
            "resumen": resumen,
            "cambios_recientes": {
                "ultima_hora": cambios_por_periodo["ultima_hora"],
                "ultimas_24h": cambios_por_periodo["hoy"],
                "ultima_semana": cambios_por_periodo["ultima_semana"],
                "ultimo_mes": cambios_por_periodo["ultimo_mes"]
            },
            "duplicados": {
                "total": len(duplicados),
                "archivos": duplicados
            },
            "tipos_archivo": {
                "total_tipos": len(tipos_archivo),
                "detalles": dict(sorted(
                    tipos_archivo.items(),
                    key=lambda x: x[1]['ultima_modificacion'],
                    reverse=True
                ))
            }
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo cambios: {str(e)}")
        return {
            "estado": "error",
            "mensaje": str(e),
            "detalles": traceback.format_exc()
        }


@app.post("/actualizar-archivos", summary="Actualizar lista de archivos desde el Excel")
async def actualizar_archivos(data: List[dict]):
    try:
        # Validar y limpiar los datos antes de procesarlos
        cleaned_data = []
        for item in data:
            try:
                cleaned_item = {
                    "Nombre": str(item.get("Nombre", "")),
                    "Ruta": str(item.get("Ruta", "")),
                    "URL": str(item.get("URL", "")),
                    "Tipo Archivo": str(item.get("Tipo Archivo", "N/A")),
                    "Fecha Creación": str(item.get("Fecha Creación", "N/A")),
                    "Fecha Modificación": str(item.get("Fecha Modificación", "N/A")),
                    "Tamaño (KB)": float(item.get("Tamaño (KB)", 0)),
                    "Categoría": str(item.get("Categoría", "Documentos compartidos")),
                    "Estado": str(item.get("Estado", "Válido")),
                }
                cleaned_data.append(cleaned_item)
            except Exception as e:
                logging.warning(f"Error procesando item: {str(e)}")
                continue

        # Crear DataFrame y guardar
        df = pd.DataFrame(cleaned_data)

        try:
            # Intentar guardar con encoding específico
            df.to_excel(EXCEL_PATH, index=False, encoding="utf-8")
            logging.info(f"Excel guardado exitosamente en: {EXCEL_PATH}")
        except Exception as excel_error:
            logging.error(f"Error guardando Excel: {str(excel_error)}")
            # Intentar con un nombre de archivo alternativo
            alt_path = os.path.join(
                os.path.dirname(EXCEL_PATH),
                f"Documentos_SharePoint_{int(time.time())}.xlsx",
            )
            df.to_excel(alt_path, index=False, encoding="utf-8")
            logging.info(f"Excel guardado en ruta alternativa: {alt_path}")

        return {
            "estado": "success",
            "mensaje": "Datos actualizados correctamente",
            "timestamp": datetime.now().isoformat(),
            "total_archivos": len(cleaned_data),
            "ruta_excel": EXCEL_PATH,
        }

    except Exception as e:
        logging.error(f"Error actualizando archivos: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# 🔹 Ejecutar API
if __name__ == "__main__":
    import uvicorn

    console.print(
        Panel.fit(
            "[bold cyan]SharePoint File Monitor API[/bold cyan]\n"
            "Versión 2.0\n"
            "Servidor iniciado en http://localhost:8000",
            title="API Monitor",
            border_style="cyan",
        )
    )
    uvicorn.run(app, host="0.0.0.0", port=8000)
