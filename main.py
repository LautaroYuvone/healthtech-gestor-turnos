from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import engine, get_db
import models
import schemas
from datetime import datetime, timezone

# 1. Creamos físicamente el archivo 'sobreturnos.db' y todas sus tablas.
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Backend con persistencia SQLite funcionando", "proyecto": "Z- Sobreturno"}


# --- RUTAS DE MÉDICOS ---

# Registrar un nuevo médico en el sistema.
@app.post("/medicos", response_model=schemas.Medico, status_code=201)
def registrar_medico(medico: schemas.Medico, db: Session = Depends(get_db)):
    # Verificamos si la matrícula ya existe para no duplicar
    db_medico = db.query(models.Medico).filter(models.Medico.matricula == medico.matricula).first()
    if db_medico:
        raise HTTPException(status_code=400, detail="La matrícula ya está registrada.")

    nuevo_medico = models.Medico(
        nombre=medico.nombre,
        especialidad=medico.especialidad,
        matricula=medico.matricula,
        direccion_consultorio=medico.direccion_consultorio,
        localidad=medico.localidad
    )
    db.add(nuevo_medico)
    db.commit()
    db.refresh(nuevo_medico)
    return nuevo_medico

# --- RUTAS DE TURNOS ---

# Buscar sobreturnos con filtros
@app.get("/turnos", response_model=list[schemas.Turno])
def obtener_turnos(
        especialidad: str | None = None,
        medico_id: int | None = None,
        db: Session = Depends(get_db)
):
    # Limpiamos la base de datos en tiempo real
    limpiar_turnos_expirados(db)

    # Traemos de la base de datos solo los turnos que estén disponibles.
    query = db.query(models.Turno).filter(models.Turno.estado == schemas.EstadoTurno.DISPONIBLE.value)

    # Filtro por médico específico
    if medico_id is not None:
        query = query.filter(models.Turno.medico_id == medico_id)

    # Filtro por especialidad
    if especialidad is not None:
        
        query = query.join(models.Medico).filter(models.Medico.especialidad.ilike(especialidad))

    return query.all()


# Publicar un sobreturno (Con validación temporal)
@app.post("/turnos", response_model=schemas.Turno, status_code=201)
def crear_turno(nuevo_turno: schemas.Turno, db: Session = Depends(get_db)):
    # 1. Validar existencia del médico
    medico_existe = db.query(models.Medico).filter(models.Medico.id == nuevo_turno.medico_id).first()
    if not medico_existe:
        raise  HTTPException(
            status_code=400,
            detail=f"No se puede crear el turno: El médico con ID {nuevo_turno.medico_id} no existe.")

    # 2. Validación temporal (Control de Fechas Pasadas)
    # Detectamos si la fecha del cliente incluye zona horaria para comparar correctamente
    ahora = datetime.now(timezone.utc) if nuevo_turno.fecha_hora.tzinfo else datetime.now()

    if nuevo_turno.fecha_hora < ahora:
        raise HTTPException(
            status_code=400,
            detail="Operación inválida: No podés publicar un sobreturno para fecha u hora pasada"
        )

    # 3. Guardar en la base de datos

    db_turno = models.Turno(
        medico_id=nuevo_turno.medico_id,
        paciente_id=None,
        fecha_hora=nuevo_turno.fecha_hora,
        tipo_turno=nuevo_turno.tipo_turno.value,
        estado=nuevo_turno.estado.value,
        precio_reserva=nuevo_turno.precio_reserva
    )
    db.add(db_turno)
    db.commit()
    db.refresh(db_turno)
    return db_turno


# FUNCIÓN DE EXPIRACIÓN AUTOMATICA (SI NO HAY RESPUESTA A LA SOLICITUD DEL TURNO)
def limpiar_turnos_expirados(db: Session, minutos_limite: int = 2):
    """
    Busca solicitudes pendientes que superen los 'minutos_limite'
    y las devuelve automáticamente al estado 'disponible'.
    """
    ahora = datetime.now(timezone.utc)

    pendientes = db.query(models.Turno).filter(
        models.Turno.estado == schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value).all()

    for turno in pendientes:
        if turno.fecha_solicitud:
            # Aseguramos compatibilidadde zona horaria
            f_solic = turno.fecha_solicitud
            if f_solic.tzinfo is None:
                f_solic = f_solic.replace(tzinfo=timezone.utc)

            minutos_transcurridos = (ahora - f_solic).total_seconds() / 60

            # Si supera el tiempo límite, se libera el turno
            if minutos_transcurridos >= minutos_limite:
                turno.estado = schemas.EstadoTurno.DISPONIBLE.value
                turno.paciente_id = None
                turno.fecha_solicitud = None

    db.commit()


# PACIENTE SOLITICTA TURNO
@app.put("/turnos/{turno_id}/solicitar", response_model=schemas.Turno)
def solicitar_turno(turno_id: int, paciente_id: int, db: Session = Depends(get_db)):
    # 1. Limpiamos tiempos expirados
    limpiar_turnos_expirados(db)

    # 2. Validar Paciente
    paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente_id).first()
    if not paciente:
        raise HTTPException(status_code=400, detail="El paciente no existe")

    # 3. Validar Turno
    db_turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()
    if not db_turno:
        raise HTTPException(status_code=404, detail="El turno no existe")

    estado_actual = str(db_turno.estado)
    if estado_actual != "disponible" and estado_actual != schemas.EstadoTurno.DISPONIBLE.value:
        raise HTTPException(status_code=400, detail=f"El turno no está disponible (Estado actual: {db_turno.estado}).")

    # GUARDAMOS EL TIMESTAMPT DE LA SOLICITUD
    db_turno.paciente_id = paciente_id
    db_turno.estado = schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value
    db_turno.fecha_solicitud = datetime.now(timezone.utc)

    db.commit()
    db.refresh(db_turno)
    return db_turno


# MEDICO ACEPTA O RECHAZA TURNO
@app.put("/turnos/{turno_id}/responder", response_model=schemas.Turno)
def responder_solicitud(turno_id: int, aceptar: bool, db: Session = Depends(get_db)):
    db_turno = db.query(models.Turno).filter(models.Turno.id == turno_id).first()
    if not db_turno:
        raise HTTPException(status_code=404, detail="El turno no existe")

    if db_turno.estado != "pendiente_confirmacion":
        raise HTTPException(status_code=400, detail="Este turno no tiene una solicitud pendiente.")

    if aceptar:
        # El médico acepta: se confirma el sobreturno y se efectiviza el cobreo
        db_turno.estado = "reservado"
    else:
        # El médico rechaza: El turno vuelve a quedar disponible o cancelado, y se simula un reembolso
        db_turno.estado = "disponible"
        db_turno.paciente_id = None # Se libera el paciente.

    db.commit()
    db.refresh(db_turno)
    return db_turno


# BANDEJA DE ENTRADA (MÉDICO): Ver solicitudes pendientes de confirmación.
@app.get("/medicos/{medico_id}/solicitudes-pendientes", response_model=list[schemas.Turno])
def obtener_solicitudes_pendientes_medico(medico_id: int, db: Session = Depends(get_db)):
    # 1. Limpiamos turnos expirados en tiempo real antes de consultar
    limpiar_turnos_expirados(db)

    # 2. Verificamos que el médico exista
    medico = db.query(models.Medico).filter(models.Medico.id == medico_id).first()
    if not medico:
        raise HTTPException(status_code=404, detail="El medico no existe")

    # 3. Buscamos sólo los turnos que estan esperando respuesta para X médico
    solicitudes = db.query(models.Turno).filter(
        models.Turno.medico_id == medico.id,
        models.Turno.estado == schemas.EstadoTurno.PENDIENTE_CONFIRMACION.value
    ).all()

    return solicitudes

# --- RUTAS DE PACIENTES ----

# Registrar un nuevo paciente en el sistema.
@app.get("/pacientes", response_model=schemas.Paciente, status_code=201)
def registrar_paciente(paciente: schemas.Paciente, db: Session = Depends(get_db)):
    # Verificamos si el ID ya existe para no duplicar (en un sistema real se buscaría por DNI o teléfono)
    db_paciente = db.query(models.Paciente).filter(models.Paciente.id == paciente.id).first()
    if db_paciente:
        raise HTTPException(status_code=400, detail="El ID de paciente ya está registrado.")

    nuevo_paciente = models.Paciente(
        nombre=paciente.nombre,
        telefono=paciente.telefono
    )
    db.add(nuevo_paciente)
    db.commit()
    db.refresh(nuevo_paciente)
    return nuevo_paciente








# from fastapi import FastAPI, HTTPException
# from datetime import datetime
# # Importamos class de schemas
# from schemas import Turno, TipoTurno, EstadoTurno, Paciente, Medico
#
# app = FastAPI()
#
# # ACTIVAMOS PONIENDO EN LA CONSOLA fastapi dev main.py
#
# # Simulamos una base de datos de médicos
# DB_MEDICOS = [
#     Medico(id=10, nombre="Dr. Juan Rodriguez", especialidad="Clinica", matricula="25670", direccion_consultorio="Rioja 1547"),
#     Medico(id=15, nombre="Dra. Ana Martinez", especialidad="Pediatria", matricula="25822", direccion_consultorio="San Martin 3215")
# ]
#
# # Simulamos una base de datos temporal
# DB_TURNOS = [
#     Turno(
#         id=1,
#         medico_id=10,
#         paciente_id=None, # DISPONIBLE, SIN PACIENTE AÚN
#         fecha_hora=datetime(2026, 7, 7, 16, 0),
#         tipo_turno=TipoTurno.SOBRETURNO,
#         estado=EstadoTurno.DISPONIBLE,
#         precio_reserva=1500.0
#     )
# ]
#
# @app.get("/")
# def home():
#     return {"status": "Backend funcionando", "proyecto": "Z - Sobreturno"}
#
# # Nuevo endpoint: Ver todos los turnos disponibles en Rosario.
# @app.get("/turnos", response_model=list[Turno]) ### GET para leer o traer datos
# def obtener_turnos(especialidad: str | None = None, medico_id: int | None = None):
#     # 1. Devolvemos solo los turnos que estén disponibles
#     resultados = [t for t in DB_TURNOS if t.estado == EstadoTurno.DISPONIBLE]
#
#     # 2. Si el paciente filtró por médico específico (?medico_id=10)
#     if medico_id is not None:
#         resultados = [t for t in resultados if t.medico_id == medico_id]
#
#     # 3. Si el paciente filtró por especialidad (?especialidad=pediatria)
#     if especialidad is not None:
#         # Buscamos que IDs de médicos coinciden con esa especialidad (ignoring mayúsculas/minúsculas)
#         ids_medicos_coincidentes = [
#             m.id for m in DB_MEDICOS if m.especialidad.lower() == especialidad.lower()
#         ]
#         # Filtramos los turnos cuyo medico_id pertenezca a esos médicos
#         resultados = [t for t in resultados if t.medico_id in ids_medicos_coincidentes]
#
#     return resultados
#
# # Nuevo endpoint: permitir que un médico publique un sobreturno
# @app.post("/turnos", response_model=Turno, status_code=201) ### POST para creas algo nuevo, desde cero.
# def crear_turno(nuevo_turno: Turno):
#     # 1. Agregamos el turno que viene desde la app a nuestra base de datos temporal
#     DB_TURNOS.append(nuevo_turno)
#
#     # 2. Devolvemos el turno creado para confirmar que se guardo bien.
#     return nuevo_turno
#
# # Reservar un turno existente
# # Usamos {turno_id} en la ruta para indicarle a FastAPI qué turno específico queremos modoficar (reservar)
# @app.put("/turnos/{turno_id}/reservar", response_model=Turno) ### PUT para modificar o actualizar un recurso ya existente.
# def reservar_turno(turno_id: int, paciente_id: int):
#     # 1. Buscamos el turno por su ID dentro de nuestra lista.
#     for turno in DB_TURNOS:
#         if turno.id == turno_id:
#
#             # 2. Control de calidad: Verificamos si el turno está disponible
#             if turno.estado != EstadoTurno.DISPONIBLE:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Operación inválida: El turno ID {turno_id} ya está {turno.estado.value}."
#                 )
#
#             # 3. Si está disponible, actualizamos campos:
#             turno.paciente_id = paciente_id
#             turno.estado = EstadoTurno.RESERVADO
#
#             # 4. Devolvemos el turno modificado para que la app del paciente sepa que se guardó bien
#             return turno
#
#     # 5. Si recorrimos toda la lista y el ID no coincidió con ninguno, tiramos un error 404
#     raise HTTPException(status_code=404, detail="El turno solicitado no existe")