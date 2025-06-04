import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cargar la URL desde las variables de entorno, si no existe usar SQLite localmente
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./obras.db")

# Para PostgreSQL no se necesita connect_args
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency para obtener la sesión de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
