import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
import bcrypt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import models, schemas, database

# Configuración del Token
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas de validez

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# --- HASHING DE CONTRASEÑAS (NATIVO CON BCRYPT) ---
def obtener_password_hash(password: str) -> str:
    # Convertimos la contraseña a bytes y generamos el hash
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')


def vericar_password(plain_password: str, hashed_password: str) -> bool:
    # Verificamos la contraseña en texto plano contra el hash guardado
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


# --- GENERACIÓN DE TOKEN JWT ---
def crear_token_acceso(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- OBTENER USUARIO ACTUAL AUTENTICADO ---
def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales de acceso.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        rol: str = payload.get("rol")
        if email is None or rol is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email, rol=rol)
    except JWTError:
        raise credentials_exception

    if token_data.rol == "medico":
        usuario = db.query(models.Medico).filter(models.Medico.email == token_data.email).first()
    else:
        usuario = db.query(models.Paciente).filter(models.Paciente.email == token_data.email).first()

    if usuario is None:
        raise credentials_exception

    return {"usuario": usuario, "rol": token_data.rol}