from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import engine, get_db
import models, schemas, auth


# 1. Creamos físicamente el archivo 'sobreturnos.db' y todas sus tablas.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Z- Sobreturno API", version="2.0")


# Función de expiración automática (Lazy Evaluation)
def limpiar_turnos_expirados(db: Session, minutos_limite: int = 2):
    ahora = datetime.now(timezone.utc)
    pendientes = db.query(models.Turno).filter(
        models.Turno.estado == schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value
    ).all()

    for turno in pendientes:
        if turno.fecha_solicitud:
            f_solic = turno.fecha_solicitud
            if f_solic.tzinfo is None:
                f_solic = f_solic.replace(tzinfo=timezone.utc)

            minutos_transcurridos = (ahora - f_solic).total_seconds() / 60
            if minutos_transcurridos >= minutos_limite:
                turno.estado = schemas.EstadoTurno.DISPONIBLE.value
                turno.paciente_id = None
                turno.fecha_solicitud = None

    db.commit()


# AUTENTICACIÓN Y LOGIN (TOKEN JWT)

@app.post("/token", response_model=schemas.Token)
def login_para_obtener_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 1. Buscamos primero en la tabla de médicos
    medico = db.query(models.Medico).filter(models.Medico.email == form_data.username).first()
    if medico and auth.vericar_password(form_data.password, medico.hashed_password):
        access_token = auth.crear_token_acceso(data={"sub": medico.email, "rol": "medico"})
        return {"access_token": access_token, "token_type": "bearer"}

    # 2. Si no es médico, buscamos en la tabla de pacientes
    paciente = db.query(models.Paciente).filter(models.Paciente.email == form_data.username).first()
    if paciente and auth.vericar_password(form_data.password, paciente.hashed_password):
        access_token = auth.crear_token_acceso(data={"sub": paciente.email, "rol": "paciente"})
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email o contraseña incorrectos.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# REGISTRO DE USUARIOS

@app.post("/medicos", response_model=schemas.Medico, status_code=201)
def registrar_medico(medico: schemas.MedicoCreate, db: Session = Depends(get_db)):
    # Validar duplicados
    if db.query(models.Medico).filter(models.Medico.email == medico.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")
    if db.query(models.Medico).filter(models.Medico.matricula == medico.matricula).first():
        raise HTTPException(status_code=400, detail="La matrícula ya está registrada.")

    hashed_pw = auth.obtener_password_hash(medico.password)
    db_medico = models.Medico(
        nombre=medico.nombre,
        especialidad=medico.especialidad,
        matricula=medico.matricula,
        direccion_consultorio=medico.direccion_consultorio,
        localidad=medico.localidad,
        email=medico.email,
        hashed_password=hashed_pw
    )
    db.add(db_medico)
    db.commit()
    db.refresh(db_medico)
    return db_medico


@app.post("/pacientes", response_model=schemas.Paciente, status_code=201)
def registrar_paciente(paciente: schemas.PacienteCreate, db: Session = Depends(get_db)):
    if db.query(models.Paciente).filter(models.Paciente.email == paciente.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado.")

    hashed_pw = auth.obtener_password_hash(paciente.password)
    db_paciente = models.Paciente(
        nombre=paciente.nombre,
        telefono=paciente.telefono,
        email=paciente.email,
        hashed_password=hashed_pw
    )
    db.add(db_paciente)
    db.commit()
    db.refresh(db_paciente)
    return db_paciente


# GESTION DE TURNOS

# Publicar turno (Solo médicos autenticados)
@app.post("/turnos", response_model=schemas.Turno, status_code=201)
def crear_turno(
    nuevo_turno: schemas.Turno,
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(auth.obtener_usuario_actual)
):
    if usuario_actual["rol"] != "medico":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los médicos pueden publicar sobreturnos.")

    medico = usuario_actual["usuario"]

    # Validar fecha futura
    ahora = datetime.now(timezone.utc) if nuevo_turno.fecha_hora.tzinfo else datetime.now()
    if nuevo_turno.fecha_hora < ahora:
        raise HTTPException(status_code=400, detail="No podés publicar un sobreturno en una fecha u hora pasada.")

    db_turno = models.Turno(
        medico_id=medico.id,  # Se vincula automáticamente al médico autenticado
        fecha_hora=nuevo_turno.fecha_hora,
        tipo_turno=nuevo_turno.tipo_turno.value,
        estado=schemas.EstadoTurno.DISPONIBLE.value,
        precio_reserva=nuevo_turno.precio_reserva
    )
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)
    return db_turno


# Buscar turnos disponibles (Público)
@app.get("/turnos", response_model=list[schemas.Turno])
def obtener_turnos(especialidad: str | None = None, db: Session = Depends(get_db)):
    limpiar_turnos_expirados(db)
    query = db.query(models.Turno).filter(models.Turno.estado == schemas.EstadoTurno.DISPONIBLE.value)

    if especialidad:
        query = query.join(models.Medico).filter(models.Medico.especialidad.ilike(f"%{especialidad}%"))

    return query.all()


# Solicitar turno (solo pacientes autenticados)
@app.put("/turnos/{turno_id}/solicitar", response_model=schemas.Turno)
def solicitar_turno(
    turno_id: int,
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(auth.obtener_usuario_actual)
):
    limpiar_turnos_expirados(db)

    if usuario_actual["rol"] != "paciente":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los pacientes pueden solicitar sobreturnos.")

    paciente = usuario_actual["usuario"]
    db_turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()

    if not db_turno:
        raise HTTPException(status_code=404, detail="El turno no existe.")
    if str(db_turno.estado) != schemas.EstadoTurno.DISPONIBLE.value:
        raise HTTPException(status_code=400, detail=f"El turno no está disponible (Estado: {db_turno.estado}).")

    db_turno.paciente_id = paciente.id  # Vincula al paciente autenticado
    db_turno.estado = schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value
    db_turno.fecha_solicitud = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_turno)
    return db_turno


# Responder solicitud (solo el médico responsable del turno)
@app.put("/turnos/{turno_id}/responder", response_model=schemas.Turno)
def responder_solicitud(
        turno_id: int,
        aceptar: bool,
        db: Session = Depends(get_db),
        usuario_actual: dict = Depends(auth.obtener_usuario_actual)
):
    if usuario_actual["rol"] != "medico":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo los médicos pueden responder solicitudes.")

    medico = usuario_actual["usuario"]
    db_turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()

    if not db_turno:
        raise HTTPException(status_code=404, detail="El turno no existe.")

    # 🔒 Candado de seguridad: Solo el médico dueño del turno puede responder
    if db_turno.medico_id != medico.id:
        raise HTTPException(status_code=403, detail="No tenés permiso para responder solicitudes de otro médico.")

    if str(db_turno.estado) != schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value:
        raise HTTPException(status_code=400, detail="Este turno no tiene una solicitud pendiente.")

    if aceptar:
        db_turno.estado = schemas.EstadoTurno.RESERVADO.value
    else:
        db_turno.estado = schemas.EstadoTurno.DISPONIBLE.value
        db_turno.paciente_id = None
        db_turno.fecha_solicitud = None

    db.commit()
    db.refresh(db_turno)
    return db_turno


# Bandeja de entrada del médico
@app.get("/medicos/me/solicitudes-pendientes", response_model=list[schemas.Turno])
def obtener_mis_solicitudes_pendientes(
    db: Session = Depends(get_db),
    usuario_actual: dict = Depends(auth.obtener_usuario_actual)
):
    limpiar_turnos_expirados(db)

    if usuario_actual["rol"] != "medico":
        raise HTTPException(status_code=403, detail="Acceso denegado.")

    medico = usuario_actual["usuario"]
    return db.query(models.Turno).filter(
        models.Turno.medico_id == medico.id,
        models.Turno.estado == schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value
    ).all()
