# HealthTech Scheduler - Sistema de Gestión de Turnos Médicos

Sistema de gestión y optimización de turnos médicos desarrollado en Python. El proyecto aborda la problemática de las cancelaciones de último momento (dentro de las 48 horas próximas al turno) y la flexibilización de la jornada profesional mediante la reasignación de turnos disponibles.

---

## Problemática Médica

En la gestión médica, el tiempo no utilizado es irrecuperable:

* **Cancelaciones tardías:** Pacientes que anulan turnos a menos de 48 horas, dejan espacios vacíos que la agenda estándar no llega a cubrir, generando pérdidas económicas e ineficiencia operativa.
* **Extensión flexible de jornada:** Profesionales que disponen de sobreturnos o bloques horarios extra en el mismo día, no cuentan con un canal ágil para demandar esa oferta inmediatamente a la comunidad de pacientes.
* **Demanda espontánea o inmediata:** Pacientes con necesidades de atención con mayor brevedad, no encuentran visibilidad de turnos liberados a último momento.

---

## Solución Propuesta

Un sistema de agendamiento dinámico que:

1. **Detecta y publica turnos en tiempo real:** Si un turno se cancela dentro de las 48 horas, el sistema lo reconvierte automáticamente en una oferta prioritaria o de "demanda inmediata"
2. **Soporta extensión de agenda profesional:** Permite al médico (o personal administrativo de este) habilitar turnos en cualquier momento de su jornada.
3. **Implementa "lazy evaluation":** Para la expiración y liberación automática de turnos no confirmados, optimizando la consulta a la base de datos sin sobrecargar la infraestructura con tareas masivas programadas.

---

## Tecnologías y Herramientas

* **Lenguaje:** Python 3.11+
* **Framework Web:** FastAPI (ASGI)
* **Servidor:** Uvicorn
* **Base de Datos:** SQLAlchemy / SQLite
* **Validación:** Pydantic (Schemas)
* **Arquitectura:** Modular (Modelos, Esquemas, Auth y Base de Datos)
* **Seguridad:** JWT (python-jose), Hashing (bcrypt, OAuth2 Bearer Tokens)
* **Testing Automatizado:** pytest, httpx (TestClient)

---

## Endpoints Principales

* **POST /token:** Autenticación unificada y generación de Token JWT.
* **POST /medicos & POST /pacientes:** Registro con claves encriptadas
* **GET /turnos:** Buscador de turnos con filtros por fecha, especialidad, tipo de turno y paginación.
* **POST /turnos:** Publicación de turnos (solo médicos autenticados)
* **PUT /turnos/{id}/solicitar:** Solicitud de reserva de sobreturno (solo pacientes autenticados).
* **PUT /turnos/{id}/responder:** Confirmación/rechazo de turnos (solo médico titular del turno)
* **GET /health**: Endpoint de monitoreo y disponibilidad del servicio de la API.

---

## 🚀 Instrucciones de Ejecución
    
```bash

# 1. Clonar repositorio y crear entorno virtual
git clone https://github.com/LautaroYuvone/healthtech-gestor-turnos.git
cd healthtech-gestor-turnos
python -m venv .venv
# En Windows: .venv\Scripts\activate
# En Linux/Mac: source .venv/bin/activate

# 2. Instalar dependencias congeladas
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env    # En Windows: copy .env.example .env

# 4. Iniciar servidor de desarrollo
fastapi dev main.py

# 5. Ejecutar suite de pruebas
pytest
```

---

## Arquitectura del Proyecto

```text
healthtech-gestor-turnos/
├── main.py            # Endpoints, lógica de negocio y máquina de estados
├── models.py          # Modelos relacionales ORM (SQLAlchemy)
├── schemas.py         # Esquemas de validación y Enums (Pydantic v2)
├── database.py        # Conexión al motor SQLite y gestión de sesiones
├── auth.py            # Seguridad, hashing con bcrypt y tokens JWT
├── test_main.py       # Suite de pruebas automatizadas (pytest)
├── requirements.txt   # Dependencias congeladas del entorno
├── .env.example       # Plantilla pública de variables de entorno
└── .gitignore         # Exclusión de base de datos local y secretos
```

