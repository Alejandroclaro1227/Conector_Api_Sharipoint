import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_files():
    response = client.get("/archivos")
    assert response.status_code == 200
    data = response.json()
    assert "archivos" in data
    assert "cambios_detectados" in data

def test_get_history():
    response = client.get("/historial")
    assert response.status_code == 200
    data = response.json()
    assert "estadisticas" in data
    assert "historial" in data 