from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.database import Base

class Obra(Base):
    __tablename__ = "obras"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String, index=True)
    sinopsis = Column(String)
    imagen_url = Column(String)
    stock = Column(Integer, default=10)
    activo = Column(Boolean, default=True)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    apellido = Column(String)
    codigo = Column(String, unique=True,)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    activo = Column(Boolean, default=True)

class LibroDisponible(Base):
    __tablename__ = "libros_disponibles"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)
    sinopsis = Column(String)
    imagen_url = Column(String)
    stock = Column(Integer, default=10)
    activo = Column(Boolean, default=True)


class LibroUsuario(Base):
    __tablename__ = "libros_usuarios"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    libro_id = Column(Integer, ForeignKey("libros_disponibles.id"))
    fecha_agregado = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")
    libro = relationship("LibroDisponible")
