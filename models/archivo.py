from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict

@dataclass
class Archivo:
    nombre: str
    tipo: str
    enlace: str
    fecha_modificacion: str
    tamano_kb: float
    hash: str
    estado: str

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Cambio:
    tipo: str
    nombre: str
    fecha_anterior: Optional[str] = None
    fecha_nueva: Optional[str] = None
    hash_anterior: Optional[str] = None
    hash_nuevo: Optional[str] = None
    fecha_creacion: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class VersionArchivo:
    nombre: str
    tipo: str
    fecha_modificacion: str
    tamano_kb: float
    estado: str
    enlace: str
    es_version_actual: bool

@dataclass
class Anomalia:
    archivos_duplicados: List[Dict]
    archivos_mismo_contenido: List[Dict]
    archivos_modificados: List[Dict]
    total_archivos: int
    
    def to_dict(self) -> Dict:
        return {
            "resumen": {
                "total_archivos": self.total_archivos,
                "archivos_duplicados": len(self.archivos_duplicados),
                "archivos_mismo_contenido": len(self.archivos_mismo_contenido),
                "archivos_modificados": len(self.archivos_modificados)
            },
            "anomalias": {
                "duplicados_por_nombre": self.archivos_duplicados,
                "duplicados_por_contenido": self.archivos_mismo_contenido,
                "modificaciones_detectadas": self.archivos_modificados
            },
            "total_archivos_analizados": self.total_archivos
        } 