from sqlalchemy.orm import Session
from app.models import Obra

def listar_obras(db: Session, activas=True):
    return db.query(Obra).filter(Obra.activo == activas).all()

def crear_obra(db: Session, titulo: str, anio: int, sinopsis: str, imagen_url: str = ""):
    nueva = Obra(titulo=titulo, anio=anio, sinopsis=sinopsis, imagen_url=imagen_url, activo=True)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

def eliminar_obra(db: Session, id: int):
    obra = db.query(Obra).filter(Obra.id == id).first()
    if obra:
        obra.activo = False
        db.commit()
    return obra
