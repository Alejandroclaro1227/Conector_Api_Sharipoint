from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

class FileInfo(BaseModel):
    nombre: str
    tipo: str
    fecha_modificacion: datetime
    tamano_kb: float
    hash: str
    estado: str

class FileResponse(BaseModel):
    archivos: List[FileInfo]
    cambios_detectados: List[Dict]
    s3_key: str | None = None

class HistoryStats(BaseModel):
    total_registros: int
    total_cambios: int
    ultima_actualizacion: datetime

class HistoryResponse(BaseModel):
    estadisticas: HistoryStats
    historial: List[Dict]

class UpdateResponse(BaseModel):
    archivos: List[FileInfo]
    total_archivos: int
    s3_key: str
    ultima_actualizacion: datetime 