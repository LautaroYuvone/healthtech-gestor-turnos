from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# 1.1 ENUMS (Opciones fijas)
class EstadoTurno(str, Enum):
    DISPONIBLE = "disponible" # Publicado por el médico
    PENDIENTE_CONFIRMACION = "pendiente_confirmacion" # Solicitado por el paciente
    RESERVADO = "reservado" # Aceptado por el médico
    RECHAZADO = "rechazado" # Rechazado por el médico
    EXPIRADO = "expirado"  # Se venció el tiempo de respuesta
    COMPLETO = "completo" # Atención realizada
    CANCELADO = "cancelado" # Cancelado por el médico/paciente.

class TipoTurno(str, Enum):
    PROGRAMADO = "programado"
    SOBRETURNO = "sobreturno"


# 1.2 Menú desplegable de especialidades médicas:
class EspecialidadMedica(str, Enum):
    CLINICA_MEDICA = "Clínica Médica"
    PEDIATRIA = "Pediatría"
    CARDIOLOGIA = "Cardiología"
    TRAUMATOLOGIA = "Traumatología"
    GINECOLOGIA = "Ginecología y Obstetricia"
    DERMATOLOGIA = "Dermatología"
    OFTALMOLOGIA = "Oftalmología"
    NEUROLOGIA = "Neurología"
    PSIQUIATRIA = "Psiquiatría"
    ODONTOLOGIA = "Odontología"
    OTORRINOLARINGOLOGIA = "Otorrinolaringología"
    GASTROENTEROLOGIA = "Gastroenterología"

# ENTIDADES INDEPENDIENTES

# 2. MÉDICOS
class MedicoBase(BaseModel):
    nombre: str
    especialidad: EspecialidadMedica
    matricula: str
    direccion_consultorio: str
    localidad: str = "Rosario"
    email: EmailStr

class MedicoCreate(MedicoBase):
    password: str # Solo se recibe al registrarse

class Medico(MedicoBase):
    id: int
    model_config = ConfigDict(from_attributes=True) # Permite mapear modelos de SQLAlchemy a Pydantic

# 3. PACIENTES
class PacienteBase(BaseModel):
    nombre: str
    telefono: str
    email: EmailStr

class PacienteCreate(PacienteBase):
    password: str

class Paciente(PacienteBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# 4. TURNOS
class Turno(BaseModel):
    id: int
    medico_id: int                        # Obligatorio: siempre sabemos que médico da el turno
    paciente_id: int | None = None        # Opcional: el turno arranca vacío (None) hasta que alguien lo reserva
    fecha_hora: datetime
    tipo_turno: TipoTurno = TipoTurno.SOBRETURNO
    estado: EstadoTurno = EstadoTurno.DISPONIBLE
    precio_reserva: float = Field(default=0.0, ge=0.0)
    fecha_solicitud: datetime | None = None

    medico: Medico | None = None
    paciente: Paciente | None = None

    model_config = ConfigDict(from_attributes=True)


# 5. TOKEN Y AUTENTICACIÓN
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str | None = None
    rol: str | None = None      # Medico o Paciente