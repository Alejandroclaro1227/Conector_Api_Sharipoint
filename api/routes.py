from fastapi import APIRouter, Depends
from typing import Dict, List
from .services import FileService
from .models import FileResponse, HistoryResponse, FileInfo, UpdateResponse
from core.config import get_settings, get_file_service
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "API funcionando"}


@router.get("/status")
async def status():
    return {"status": "online"}


@router.get(
    "/archivos",
    response_model=FileResponse,
    summary="Obtener lista de archivos con historial y cambios",
    response_description="Lista de archivos y cambios detectados",
)
async def get_files(service: FileService = Depends(), settings=Depends(get_settings)):
    archivos, cambios = await service.process_files()
    return FileResponse(archivos=archivos, cambios_detectados=cambios)


@router.get(
    "/historial",
    response_model=HistoryResponse,
    summary="Obtener historial completo de cambios",
)
async def get_history(service: FileService = Depends(), settings=Depends(get_settings)):
    history = await service.get_history()
    return HistoryResponse(**history)


@router.get(
    "/actualizar",
    summary="Actualizar archivos desde SharePoint y guardar en S3",
    response_description="Resultado de la actualización",
)
async def update_files(
    service: FileService = Depends(get_file_service),
    settings: Settings = Depends(get_settings),
):
    result = await service.process_and_upload()
    return JSONResponse(content=result)
