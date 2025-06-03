from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioLogin

router = APIRouter()
SECRET_KEY = "admin"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def crear_token(data: dict, expires_minutes: int = 30):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not pwd_context.verify(password, usuario.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = crear_token({"sub": usuario.email})

    # Guardar token en cookie (opcional) o redirigir
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="token", value=token)
    return response

@router.post("/registro")
def registrar_usuario(
    nombre: str = Form(...),
    apellido: str = Form(...),
    codigo: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    if db.query(Usuario).filter(Usuario.codigo == codigo).first():
        raise HTTPException(status_code=400, detail="El código ya está en uso")

    hashed_password = pwd_context.hash(password)
    nuevo_usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        codigo=codigo,
        email=email,
        password=hashed_password
    )
    db.add(nuevo_usuario)
    db.commit()

    return RedirectResponse(url="/login", status_code=303)
