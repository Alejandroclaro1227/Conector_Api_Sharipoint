from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
from fastapi import HTTPException
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import io

class SharePointService:
    def __init__(self, settings):
        self.settings = settings
        self.ctx = self._connect_to_sharepoint()
        
    def _connect_to_sharepoint(self):
        try:
            credentials = UserCredential(
                self.settings.SHAREPOINT_USERNAME, 
                self.settings.SHAREPOINT_PASSWORD
            )
            ctx = ClientContext(self.settings.SHAREPOINT_SITE_URL).with_credentials(credentials)
            return ctx
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error conectando a SharePoint: {str(e)}")
    
    async def get_files(self) -> List[Dict]:
        try:
            folder = self.ctx.web.get_folder_by_server_relative_url(self.settings.SHAREPOINT_FOLDER_URL)
            files = folder.files
            self.ctx.load(files)
            self.ctx.execute_query()
            
            processed_files = []
            for file in files:
                file_info = {
                    "nombre": file.name,
                    "tipo": self._get_file_type(file.name),
                    "ruta": file.serverRelativeUrl,
                    "enlace": f"https://cuneduco.sharepoint.com{file.serverRelativeUrl}",
                    "fecha_creacion": file.time_created,
                    "fecha_modificacion": file.time_last_modified,
                    "tamano_kb": round(file.length / 1024, 2) if file.length else 0
                }
                processed_files.append(file_info)
            
            return processed_files
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error obteniendo archivos: {str(e)}")
    
    def _get_file_type(self, filename: str) -> str:
        if "." not in filename:
            return "Desconocido"
        ext = filename.split(".")[-1].lower()
        types = {
            "pdf": "PDF",
            "doc": "Word", "docx": "Word",
            "xls": "Excel", "xlsx": "Excel",
            "csv": "CSV",
            "txt": "Texto"
        }
        return types.get(ext, "Otro")

class S3Service:
    def __init__(self, s3_client, settings):
        self.s3_client = s3_client
        self.settings = settings
    
    async def upload_excel(self, df: pd.DataFrame) -> str:
        try:
            # Crear buffer en memoria
            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            
            # Generar nombre del archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            key = f"documentos/SharePoint_Files_{timestamp}.xlsx"
            
            # Subir a S3
            await self.s3_client.put_object(
                Bucket=self.settings.AWS_BUCKET_NAME,
                Key=key,
                Body=excel_buffer.getvalue()
            )
            
            return key
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error S3: {str(e)}")

class FileService:
    def __init__(self, sharepoint_service: SharePointService, s3_service: S3Service):
        self.sharepoint = sharepoint_service
        self.s3 = s3_service
    
    async def process_and_upload(self) -> Dict:
        # Obtener archivos de SharePoint
        files = await self.sharepoint.get_files()
        
        # Crear DataFrame
        df = pd.DataFrame(files)
        
        # Subir a S3
        s3_key = await self.s3.upload_excel(df)
        
        return {
            "archivos": files,
            "total_archivos": len(files),
            "s3_key": s3_key,
            "ultima_actualizacion": datetime.now().isoformat()
        } 