from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class Medico(Base):
    __tablename__ = 'medicos'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    especialidad = Column(String, nullable=False)
    matricula = Column(String, unique=True, nullable=False)
    direccion_consultorio = Column(String, nullable=False)
    localidad = Column(String, default='Rosario')

    # CAMPOS DE AUTENTICACIÓN (MÉDICO)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Relación: un médico puede publicar muchos sobreturnos
    turnos = relationship("Turno", back_populates="medico")


class Paciente(Base):
    __tablename__ = 'pacientes'

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=False)

    # CAMPOS DE AUTENTICACIÓN (PACIENTE)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Relación: Un paciente puede reservar muchos turnos.
    turnos = relationship("Turno", back_populates="paciente")


class Turno(Base):
    __tablename__ = 'turnos'

    id = Column(Integer, primary_key=True, index=True)
    medico_id = Column(Integer, ForeignKey('medicos.id'), nullable=False)
    paciente_id = Column(Integer, ForeignKey('pacientes.id'), nullable=True)
    fecha_hora = Column(DateTime, nullable=False)
    tipo_turno = Column(String, default='sobreturno')
    estado = Column(String, default='disponible')
    precio_reserva = Column(Float, default=0.0)

    # Guardamos la hora exacta de la solicitud
    fecha_solicitud = Column(DateTime, nullable=True)

    # Relaciones:
    medico = relationship("Medico", back_populates="turnos")
    paciente = relationship("Paciente", back_populates="turnos")