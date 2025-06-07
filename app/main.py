from fastapi import FastAPI, Request, Form, Depends, HTTPException, Cookie, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER
from app.database import engine, SessionLocal, get_db
from app import models, crud, auth
from app.auth import router as auth_router, SECRET_KEY, ALGORITHM, crear_token
from app import models
from jose import jwt
import shutil
import os
import requests
from shutil import copyfileobj
from passlib.context import CryptContext
import socket

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router, prefix="/auth")
os.makedirs("static/uploads", exist_ok=True)
IMGUR_CLIENT_ID = "6b890e02442e247"

from passlib.context import CryptContext
from app.models import Usuario, Obra, LibroDisponible

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def subir_a_imgur(archivo: UploadFile):
    headers = {"Authorization": f"Client-ID {IMGUR_CLIENT_ID}"}
    image_data = archivo.file.read()

    response = requests.post(
        "https://api.imgur.com/3/image",
        headers=headers,
        files={"image": image_data}
    )

    if response.status_code == 200:
        return response.json()['data']['link']
    else:
        raise Exception("Error al subir imagen a Imgur")


def guardar_imagen_upload(file: UploadFile) -> str:
    carpeta_destino = "app/static/uploads"
    os.makedirs(carpeta_destino, exist_ok=True)  # Crea la carpeta si no existe
    ruta_archivo = os.path.join(carpeta_destino, file.filename)
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return f"/static/uploads/{file.filename}"  # Esto es lo que guardarás en la DB

@app.on_event("startup")
def crear_admin():
    db = SessionLocal()
    existe = db.query(Usuario).filter(Usuario.email == "admin@admin.com").first()
    if not existe:
        admin = Usuario(
            nombre="Admin",
            apellido="Principal",
            codigo="0000",
            email="admin@admin.com",
            password=pwd_context.hash("admin123")  # ← CONTRASEÑA AQUÍ
        )
        db.add(admin)
        db.commit()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db), q: str = ""):
    query = db.query(models.LibroDisponible).filter(models.LibroDisponible.stock > 0, models.LibroDisponible.activo == True)
    if q:
        query = query.filter(models.LibroDisponible.titulo.ilike(f"%{q}%"))
    libros = query.all()
    return templates.TemplateResponse("home.html", {"request": request, "libros": libros, "q": q})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), token: str = Cookie(None)):
    if not token:
        return RedirectResponse("/login", status_code=303)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email = payload.get("sub")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if usuario.email == "admin@admin.com":
        usuarios = db.query(Usuario).all()
        datos = []
        for u in usuarios:
            libros_u = db.query(models.LibroUsuario).filter_by(usuario_id=u.id).all()
            datos.append({"usuario": u, "libros": libros_u})

        estado = request.query_params.get("estado")
        q = request.query_params.get("q", "")

        disponibles_query = db.query(models.LibroDisponible)

        if estado == "activo":
            disponibles_query = disponibles_query.filter(models.LibroDisponible.activo == True)
        elif estado == "inactivo":
            disponibles_query = disponibles_query.filter(models.LibroDisponible.activo == False)

        if q:
            disponibles_query = disponibles_query.filter(models.LibroDisponible.titulo.ilike(f"%{q}%"))

        disponibles = disponibles_query.all()

        for libro in disponibles:
            libro.usuarios = (
                db.query(models.LibroUsuario)
                .filter_by(libro_id=libro.id)
                .join(models.Usuario)
                .all()
            )

        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "datos": datos,
            "disponibles": disponibles,
            "usuario": usuario,
            "hide_navbar": True
        })

    libros = db.query(models.LibroUsuario).filter(models.LibroUsuario.usuario_id == usuario.id).all()
    disponibles_query = db.query(models.LibroDisponible).filter(models.LibroDisponible.stock > 0,
                                                                models.LibroDisponible.activo == True)
    if request.query_params.get("q"):
        disponibles_query = disponibles_query.filter(
            models.LibroDisponible.titulo.ilike(f"%{request.query_params.get('q')}%"))
    disponibles = disponibles_query.all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "libros": libros,
        "disponibles": disponibles,
        "usuario": usuario
    })



@app.post("/obras/{id}/eliminar")
def eliminar_obra(id: int, db: Session = Depends(get_db)):
    crud.eliminar_obra(db, id)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/desarrollador")
def desarrollador():
    return {"nombre": "Juan Pablo Torres", "código": "67001446", "email": "jptorres46@ucatolica.edu.co"}

@app.get("/planeacion")
def planeacion():
    return {
        "casos_de_uso": "Registrar, consultar, modificar y eliminar obras literarias",
        "modelo_de_datos": "Obra(id, título, año, sinopsis, activo, imagen_url)",
        "fuente_datos": "Obras de Mario Mendoza, recolectadas manualmente"
    }

@app.get("/diseno")
def diseno():
    return {
        "diagrama_clases": "Incluido en la documentación del repositorio",
        "endpoints": ["/", "/dashboard", "/auth/login", "/obras/crear", "/obras/{id}/eliminar"],
        "mockups": "Vistas: login, home, dashboard"
    }

@app.post("/obras/{id}/alternar")
def alternar_estado_obra(id: int, db: Session = Depends(get_db)):
    obra = db.query(LibroDisponible).filter(LibroDisponible.id == id).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    obra.activo = not obra.activo
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/obras")
def listar_obras(db: Session = Depends(get_db)):
    obras = db.query(Obra).filter(Obra.activo == True).all()
    return obras

@app.get("/login", response_class=HTMLResponse)
def mostrar_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def mostrar_registro(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("token")  # Elimina la cookie del JWT
    return response

@app.post("/usuarios/{usuario_id}/alternar")
def alternar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = not usuario.activo
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/agregar-libro/{libro_id}")
def agregar_libro(libro_id: int, request: Request, db: Session = Depends(get_db), token: str = Cookie(None)):
    if not token:
        return RedirectResponse("/login", status_code=303)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except:
        return RedirectResponse("/login", status_code=303)

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()

    libro = db.query(models.LibroDisponible).filter(models.LibroDisponible.id == libro_id).first()
    if not libro or libro.stock <= 0:
        raise HTTPException(status_code=404, detail="Libro no disponible")

    # Verifica si ya lo tiene
    existente = db.query(models.LibroUsuario).filter_by(usuario_id=usuario.id, libro_id=libro.id).first()
    if existente:
        return RedirectResponse(url="/dashboard", status_code=303)

    libro.stock -= 1
    nuevo = models.LibroUsuario(usuario_id=usuario.id, libro_id=libro.id)
    db.add(nuevo)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/quitar-libro/{relacion_id}")
def quitar_libro(relacion_id: int, db: Session = Depends(get_db), token: str = Cookie(None)):
    if not token:
        return RedirectResponse("/login", status_code=303)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except:
        return RedirectResponse("/login", status_code=303)

    usuario = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    relacion = db.query(models.LibroUsuario).filter_by(id=relacion_id, usuario_id=usuario.id).first()

    if not relacion:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    # Devolver stock
    libro = db.query(models.LibroDisponible).filter_by(id=relacion.libro_id).first()
    libro.stock += 1

    db.delete(relacion)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/obras/crear")
async def crear_obra(
    titulo: str = Form(...),
    sinopsis: str = Form(...),
    imagen: UploadFile = File(...),
    stock: int = Form(...),
    db: Session = Depends(get_db)
):
    os.makedirs("app/static/uploads", exist_ok=True)
    extension = os.path.splitext(imagen.filename)[1]
    nombre_archivo = titulo.replace(" ", "_").lower() + extension
    ruta_destino = os.path.join("app", "static", "uploads", nombre_archivo)

    with open(ruta_destino, "wb") as buffer:
        shutil.copyfileobj(imagen.file, buffer)

    imagen_url = f"/static/uploads/{nombre_archivo}"

    nuevo = models.LibroDisponible(
        titulo=titulo,
        sinopsis=sinopsis,
        imagen_url=imagen_url,
        stock=stock,
        activo=True
    )
    db.add(nuevo)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/obras/{obra_id}/stock")
def actualizar_stock(obra_id: int, stock: int = Form(...), db: Session = Depends(get_db)):
    obra = db.query(models.LibroDisponible).filter(models.LibroDisponible.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")
    obra.stock = stock
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


libros = [
        {
            "titulo": "Satanás",
            "sinopsis": "Basada en hechos reales, narra el descenso de un exmilitar en la locura y la violencia.",
            "imagen_url": "/static/uploads/satanas.jpg"
        },
        {
            "titulo": "La ciudad de los umbrales",
            "sinopsis": "Un joven enfrenta misterios ocultos en Bogotá mientras busca sentido a su existencia.",
            "imagen_url": "/static/uploads/ciudad_umbrales.jpg"
        },
        {
            "titulo": "El viaje del loco Tafur",
            "sinopsis": "Una travesía mística y filosófica por América Latina en busca de conocimiento oculto.",
            "imagen_url": "/static/uploads/viaje_tafur.jpg"
        },
        {
            "titulo": "Apocalipsis",
            "sinopsis": "Un periodista descubre una red global que lleva al fin del mundo tal como lo conocemos.",
            "imagen_url": "/static/uploads/apocalipsis.jpg"
        },
        {
            "titulo": "Lady Masacre",
            "sinopsis": "Una joven víctima de violencia se transforma en una asesina justiciera.",
            "imagen_url": "/static/uploads/lady_masacre.jpg"
        },
        {
            "titulo": "La melancolía de los feos",
            "sinopsis": "Reflexión sobre la belleza, la marginación y el valor de lo invisible.",
            "imagen_url": "/static/uploads/melancolia.jpg"
        },
        {
            "titulo": "Akelarre",
            "sinopsis": "Tres mujeres conectadas por un mismo destino ancestral luchan por su libertad.",
            "imagen_url": "/static/uploads/akelarre.jpg"
        },
        {
            "titulo": "Bitácora del naufragio",
            "sinopsis": "Ensayo y ficción se mezclan para contar el derrumbe de una sociedad.",
            "imagen_url": "/static/uploads/naufragio.jpg"
        },
        {
            "titulo": "Scorpio City",
            "sinopsis": "Una visión futurista y decadente de Bogotá donde el crimen lo domina todo.",
            "imagen_url": "/static/uploads/scorpio.jpg"
        },
        {
            "titulo": "El año del verano que nunca llegó",
            "sinopsis": "Un viaje a Europa sobre escritores, monstruos y los orígenes del horror moderno.",
            "imagen_url": "/static/uploads/verano.jpg"
        }
    ]

@app.post("/obras/{id}/eliminar-definitivo")
def eliminar_definitivo(id: int, db: Session = Depends(get_db)):
    obra = db.query(models.LibroDisponible).filter(models.LibroDisponible.id == id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    db.delete(obra)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/usuarios/{id}/eliminar")
def eliminar_usuario(id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter_by(id=id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Borra relaciones con libros si existen
    db.query(models.LibroUsuario).filter_by(usuario_id=id).delete()

    db.delete(usuario)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/obras/{id}/actualizar")
def actualizar_obra(
    id: int,
    titulo: str = Form(...),
    sinopsis: str = Form(...),
    stock: int = Form(...),
    imagen: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    obra = db.query(LibroDisponible).filter(LibroDisponible.id == id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    obra.titulo = titulo
    obra.sinopsis = sinopsis
    obra.stock = stock

    if imagen:
        os.makedirs("app/static/uploads", exist_ok=True)
        filename = f"{titulo.lower().replace(' ', '_')}.jpg"
        ruta_destino = os.path.join("app", "static", "uploads", filename)
        with open(ruta_destino, "wb") as buffer:
            shutil.copyfileobj(imagen.file, buffer)
        obra.imagen_url = f"/static/uploads/{filename}"

    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)