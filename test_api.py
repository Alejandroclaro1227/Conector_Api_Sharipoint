import requests
import json
from datetime import datetime
import time


class APITester:
    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url

    def test_get_archivos(self):
        print("\n=== Probando GET /archivos ===")
        response = requests.get(f"{self.base_url}/archivos")
        self._print_response(response)

    def test_get_cambios(self):
        print("\n=== Probando GET /cambios ===")
        response = requests.get(f"{self.base_url}/cambios")
        self._print_response(response)

    def test_get_historico(self):
        print("\n=== Probando GET /historico ===")
        response = requests.get(f"{self.base_url}/historico")
        self._print_response(response)

    def test_actualizar_archivos(self, datos):
        print("\n=== Probando POST /actualizar-archivos ===")
        response = requests.post(f"{self.base_url}/actualizar-archivos", json=datos)
        self._print_response(response)

    def _print_response(self, response):
        print(f"Status Code: {response.status_code}")
        print("Response:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)


def main():
    tester = APITester()

    # Probar todos los endpoints
    tester.test_get_archivos()
    time.sleep(1)

    tester.test_get_cambios()
    time.sleep(1)

    tester.test_get_historico()
    time.sleep(1)

    # Datos de prueba para actualizar
    datos_prueba = [
        {
            "Nombre": "test_file.pdf",
            "Ruta": "/test/test_file.pdf",
            "URL": "https://example.com/test_file.pdf",
            "Tipo Archivo": "PDF",
            "Fecha Creación": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Fecha Modificación": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Tamaño (KB)": 1024,
            "Categoría": "Test",
            "Estado": "Válido",
        }
    ]

    tester.test_actualizar_archivos(datos_prueba)


if __name__ == "__main__":
    main()
