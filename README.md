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

---

## 🚀 Instrucciones de Ejecución

1. **Clonar e instalar dependencias:**
   ```bash
   git clone https://github.com/LautaroYuvone/healthtech-gestor-turnos.git
   cd healthtech-gestor-turnos
   python -m venv .venv
   # En Windows: .venv\Scripts\activate
   # En Linux/Mac: source .venv/bin/activate
   pip install fastapi uvicorn sqlalchemy pydantic

---

## Arquitectura del Proyecto

```text
healthtech-gestor-turnos/
│
├── main.py        # Lógica principal y endpoints
├── models.py      # Modelos ORM (Pacientes, Profesionales, Turnos, Huecos)
├── schemas.py     # Validación de datos con Pydantic
├── database.py    # Conexión a base de datos y sesiones
├── auth.py        # Módulo de seguridad, hashing y emisión de JWT
└── .gitignore     # Exclusión de archivos sensibles y base de datos local


