import pandas as pd
import hashlib
from typing import Tuple, List, Dict, Optional
import logging
from threading import Thread
import time

from models.archivo import Archivo, Cambio, Anomalia
from repositories.archivo_repository import ArchivoRepository
from config import config

logger = logging.getLogger(__name__)

class ArchivoService:
    def __init__(self):
        self.repository = ArchivoRepository()
        self._iniciar_sincronizacion()

    def _iniciar_sincronizacion(self):
        thread = Thread(target=self._sincronizacion_automatica, daemon=True)
        thread.start()

    def _sincronizacion_automatica(self):
        while True:
            try:
                logger.info("🔄 Sincronizando archivos desde Excel...")
                self.obtener_archivos()
                logger.info(f"✅ Sincronización completada. Esperando {config.SYNC_INTERVAL // 60} minutos...")
                time.sleep(config.SYNC_INTERVAL)
            except Exception as e:
                logger.error(f"Error en sincronización: {e}")

    def calcular_hash(self, file_data: str) -> str:
        hasher = hashlib.sha256()
        hasher.update(str(file_data).encode('utf-8'))
        return hasher.hexdigest()

    def obtener_archivos(self) -> Tuple[List[Archivo], List[Cambio]]:
        df = self.repository.leer_excel()
        historial = self.repository.cargar_historial()
        
        archivos = []
        cambios = []
        nuevo_historial = {}

        for _, row in df.iterrows():
            try:
                archivo, cambio = self._procesar_archivo(row, historial)
                archivos.append(archivo)
                if cambio:
                    cambios.append(cambio)
                
                nuevo_historial[archivo.nombre] = {
                    "fecha_modificacion": archivo.fecha_modificacion,
                    "tamano_kb": archivo.tamano_kb,
                    "hash": archivo.hash,
                    "estado": archivo.estado
                }
            except Exception as e:
                logger.error(f"Error procesando archivo: {e}")

        self.repository.guardar_historial(nuevo_historial)
        return archivos, cambios

    def _procesar_archivo(self, row: pd.Series, historial: Dict) -> Tuple[Archivo, Optional[Cambio]]:
        nombre = row["Nombre del Documento"]
        enlace = row["Punto B"]
        fecha_modificacion = str(row["Última Modificación"])
        tamano_archivo = round(row["Tamaño (KB)"], 2)
        
        file_data = f"{nombre}|{fecha_modificacion}|{tamano_archivo}"
        hash_actual = self.calcular_hash(file_data)
        
        estado = config.ESTADO_VALIDO
        cambio = None

        if nombre in historial:
            archivo_anterior = historial[nombre]
            if archivo_anterior["hash"] != hash_actual:
                estado = config.ESTADO_MODIFICADO
                cambio = Cambio(
                    tipo=config.ESTADO_MODIFICADO,
                    nombre=nombre,
                    fecha_anterior=archivo_anterior["fecha_modificacion"],
                    fecha_nueva=fecha_modificacion,
                    hash_anterior=archivo_anterior["hash"],
                    hash_nuevo=hash_actual
                )
        else:
            estado = config.ESTADO_NUEVO
            cambio = Cambio(
                tipo=config.ESTADO_NUEVO,
                nombre=nombre,
                fecha_creacion=row["Fecha de Creación"]
            )

        archivo = Archivo(
            nombre=nombre,
            tipo=nombre.split(".")[-1].upper(),
            enlace=enlace,
            fecha_modificacion=fecha_modificacion,
            tamano_kb=tamano_archivo,
            hash=hash_actual,
            estado=estado
        )

        return archivo, cambio

    def detectar_anomalias(self) -> Anomalia:
        archivos, _ = self.obtener_archivos()
        
        archivos_por_nombre = {}
        archivos_por_hash = {}
        anomalias_duplicados = []
        anomalias_contenido = []
        anomalias_modificados = []

        # Agrupar archivos
        for archivo in archivos:
            nombre_base = archivo.nombre.split(" (")[0].replace("(1)", "").strip()
            if nombre_base not in archivos_por_nombre:
                archivos_por_nombre[nombre_base] = []
            archivos_por_nombre[nombre_base].append(archivo)

            if archivo.hash not in archivos_por_hash:
                archivos_por_hash[archivo.hash] = []
            archivos_por_hash[archivo.hash].append(archivo)

        # Procesar duplicados
        for nombre_base, versiones in archivos_por_nombre.items():
            if len(versiones) > 1:
                anomalias_duplicados.append(self._procesar_versiones(nombre_base, versiones))

        # Procesar contenido idéntico
        for hash_valor, archivos_iguales in archivos_por_hash.items():
            if len(archivos_iguales) > 1:
                anomalias_contenido.append(self._procesar_contenido_identico(hash_valor, archivos_iguales))

        return Anomalia(
            archivos_duplicados=anomalias_duplicados,
            archivos_mismo_contenido=anomalias_contenido,
            archivos_modificados=anomalias_modificados,
            total_archivos=len(archivos)
        ) 