from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import os
import pandas as pd
from dotenv import load_dotenv
import time
from datetime import datetime
import schedule
import logging
import json
from pathlib import Path
import sys
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
import requests

# Configuración de Rich para una mejor visualización
console = Console()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("sharepoint_sync.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Cargar variables de entorno
load_dotenv(".env")

# Configuración
SITE_URL = os.getenv("SHAREPOINT_SITE_URL")
FOLDER_URL = os.getenv("SHAREPOINT_FOLDER_URL")
USERNAME = os.getenv("SHAREPOINT_USERNAME")
PASSWORD = os.getenv("SHAREPOINT_PASSWORD")
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "2"))  # minutos
HISTORY_FILE = "sync_history.json"
EXCEL_FILE = "Documentos_SharePoint.xlsx"


class SharePointMonitor:
    def __init__(self):
        self.console = Console()
        self.history = self.load_history()

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        return {"last_sync": None, "total_syncs": 0, "changes_detected": 0}

    def save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=4)

    def connect_to_sharepoint(self):
        with Progress() as progress:
            task = progress.add_task("[cyan]Conectando a SharePoint...", total=1)
            try:
                credentials = UserCredential(USERNAME, PASSWORD)
                ctx = ClientContext(SITE_URL).with_credentials(credentials)
                web = ctx.web
                ctx.load(web)
                ctx.execute_query()
                progress.update(task, advance=1)
                self.console.print(
                    f"[green]✓ Conexión exitosa a: {web.properties['Title']}"
                )
                return ctx
            except Exception as e:
                self.console.print(f"[red]✗ Error de conexión: {str(e)}")
                return None

    def get_file_stats(self, files):
        total_size = sum(file.length for file in files if file.length)
        avg_size = total_size / len(files) if files else 0
        return {
            "total": len(files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "avg_size_kb": round(avg_size / 1024, 2),
        }

    def create_file_table(self, files, title):
        table = Table(title=title)
        table.add_column("Nombre", style="cyan")
        table.add_column("Tamaño (KB)", justify="right", style="green")
        table.add_column("Última Modificación", style="magenta")

        for file in files:
            table.add_row(
                file["Nombre"],
                str(round(file["Tamaño (KB)"], 2)),
                str(file["Fecha Modificación"]),
            )
        return table

    def sync_files(self):
        start_time = time.time()
        sync_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.console.print(
            Panel(f"[bold cyan]Iniciando sincronización - {sync_timestamp}")
        )

        ctx = self.connect_to_sharepoint()
        if not ctx:
            return

        with Progress() as progress:
            task1 = progress.add_task("[green]Obteniendo archivos...", total=1)
            folder = ctx.web.get_folder_by_server_relative_url(FOLDER_URL)
            files = folder.files

            # Cargar todas las propiedades necesarias
            ctx.load(
                files,
                [
                    "ServerRelativeUrl",
                    "Name",
                    "TimeCreated",
                    "TimeLastModified",
                    "Length",
                    "ListItemAllFields",
                ],
            )
            ctx.execute_query()
            progress.update(task1, advance=1)

            task2 = progress.add_task(
                "[yellow]Procesando archivos...", total=len(files)
            )
            processed_files = []

            for file in files:
                try:
                    # Obtener extensión del archivo
                    file_extension = (
                        os.path.splitext(file.name)[1].lower().replace(".", "").upper()
                    )
                    if not file_extension:
                        file_extension = "Sin extensión"

                    # Construir URL de SharePoint
                    file_path = file.server_relative_url.split(
                        "/Documentos compartidos/"
                    )[-1]
                    sharepoint_url = (
                        f"https://cuneduco.sharepoint.com/sites/Vicerrectoras/Documentos%20compartidos/"
                        f"{file_path.replace(' ', '%20')}"
                    )

                    # Formatear fechas
                    created_date = (
                        file.time_created.strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(file, "time_created") and file.time_created
                        else "N/A"
                    )
                    modified_date = (
                        file.time_last_modified.strftime("%Y-%m-%d %H:%M:%S")
                        if hasattr(file, "time_last_modified")
                        and file.time_last_modified
                        else "N/A"
                    )

                    file_info = {
                        "Nombre": file.name,
                        "Ruta": file_path,
                        "URL": sharepoint_url,
                        "Tipo Archivo": file_extension,
                        "Fecha Creación": created_date,
                        "Fecha Modificación": modified_date,
                        "Tamaño (KB)": (
                            round(file.length / 1024, 2) if file.length else 0
                        ),
                        "Categoría": "Documentos compartidos",
                        "Estado": "Válido",
                    }
                    processed_files.append(file_info)
                    progress.update(task2, advance=1)

                except Exception as e:
                    self.console.print(
                        f"[red]Error procesando archivo {file.name}: {str(e)}"
                    )
                    continue

            # Crear DataFrame con todas las columnas
            df = pd.DataFrame(processed_files)

            # Asegurar el orden correcto de las columnas
            columns_order = [
                "Nombre",
                "Ruta",
                "URL",
                "Tipo Archivo",
                "Fecha Creación",
                "Fecha Modificación",
                "Tamaño (KB)",
                "Categoría",
                "Estado",
            ]

            df = df[columns_order]

            # Guardar Excel
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            excel_path = os.path.join(output_dir, EXCEL_FILE)

            try:
                df.to_excel(excel_path, index=False)
                self.console.print(
                    f"[green]Excel guardado exitosamente en: {excel_path}"
                )

                # Después de guardar el Excel, enviar datos a la API
                json_data = []
                for file_info in processed_files:
                    try:
                        json_data.append({
                            "Nombre": file_info["Nombre"],
                            "Ruta": file_info["Ruta"],
                            "URL": file_info["URL"],
                            "Tipo Archivo": os.path.splitext(file_info["Nombre"])[1].upper().replace('.', '') or 'N/A',
                            "Fecha Creación": file_info["Fecha Creación"],
                            "Fecha Modificación": file_info["Fecha Modificación"],
                            "Tamaño (KB)": file_info["Tamaño (KB)"],
                            "Categoría": file_info["Categoría"],
                            "Estado": file_info["Estado"]
                        })
                    except Exception as e:
                        self.console.print(f"[yellow]Error procesando archivo para API: {str(e)}[/yellow]")
                        continue
                
                # Enviar datos a la API
                api_url = "http://localhost:8000/actualizar-archivos"
                response = requests.post(api_url, json=json_data)
                
                if response.status_code == 200:
                    self.console.print("[green]✓ Datos enviados exitosamente a la API")
                else:
                    self.console.print(f"[yellow]Error al enviar datos a la API: {response.status_code}")

                # Mostrar resumen con más detalles
                self.console.print(
                    "\n[bold cyan]Resumen de la sincronización:[/bold cyan]"
                )
                self.console.print(f"• Archivos procesados: {len(processed_files)}")
                self.console.print(
                    f"• Tipos de archivo encontrados: {', '.join(df['Tipo Archivo'].unique())}"
                )
                self.console.print(f"• Tamaño total: {df['Tamaño (KB)'].sum():.2f} KB")

            except Exception as e:
                self.console.print(f"[red]Error al guardar el Excel: {str(e)}")

        # Actualizar estadísticas
        execution_time = round(time.time() - start_time, 2)

        # Actualizar historial
        self.history["last_sync"] = sync_timestamp
        self.history["total_syncs"] += 1
        self.history["changes_detected"] += len(processed_files)
        self.save_history()

        self.console.print("\n" + "=" * 50 + "\n")


def main():
    monitor = SharePointMonitor()

    # Mostrar banner inicial
    console.print(
        Panel.fit(
            "[bold cyan]SharePoint File Monitor[/bold cyan]\n"
            f"Intervalo de sincronización: {SYNC_INTERVAL} minutos\n"
            "Presiona Ctrl+C para detener",
            title="Iniciando monitoreo",
            border_style="cyan",
        )
    )

    # Primera sincronización
    monitor.sync_files()

    # Programar sincronizaciones posteriores
    schedule.every(SYNC_INTERVAL).minutes.do(monitor.sync_files)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Deteniendo monitoreo...[/yellow]")
        console.print(
            Panel(
                f"Total de sincronizaciones: {monitor.history['total_syncs']}\n"
                f"Cambios detectados: {monitor.history['changes_detected']}\n"
                f"Última sincronización: {monitor.history['last_sync']}",
                title="Resumen final",
                border_style="yellow",
            )
        )


if __name__ == "__main__":
    main()
