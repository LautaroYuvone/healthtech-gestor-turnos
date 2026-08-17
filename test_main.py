from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. Test del endpoint de estado
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

# 2. Test de registro de paciente
def test_registro_paciente():
    payload = {
        "nombre": "Paciente Test",
        "telefono": "3411234567",
        "email": "paciente.test@gmail.com",
        "password": "password123"
    }
    response = client.post("/pacientes", json=payload)
    assert response.status_code in [201, 400] # 200 si el paciente es nuevo, 400 si ya existe en la DB local

# 3. Test de login y obtención de token JWT
def test_login_invalido():
    response = client.post(
        "/token",
        data={"username": "noexiste@gmail.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

# 4. Test del buscador público de turnos
def test_buscador_turnos():
    response = client.get("/turnos?limite=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
