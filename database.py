from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Definimos la URL de la base de datos.
# Para desarrollo usamos SQLite. Creará un archivo llamado "sobreturnos.db" en la carpeta del proyecto
# Si quisieramos cambiar a MySQL en producción, solo cambiamos esta linea por:
# DATABASE_URL = "mysql+pymysql://usuario:contraseña@localhost/nombre_db"
DATABASE_URL = "sqlite:///./sobreturnos.db"

# 2. Creamos el motor de la base de datos.
# El argumento 'check_same_thread' es exclusivo y necesario para SQLite en FastAPI.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 3. Creamos una fábrica de sesiones (las que usamos para hacer consultas/guardar datos)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Creamos la clase Base. De acá van a heredar nuestros modelos de base de datos.
Base = declarative_base()

# 5. Función auxiliar (Dependency) para abrir y cerrar la conexión automáticamente en cada ruta.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()