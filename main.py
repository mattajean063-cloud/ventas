import os
from fastapi import FastAPI, Request, Form, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Set, Optional
import shutil

# Importaciones para SQLAlchemy y conexión a Supabase Postgres
from sqlalchemy import create_engine, Column, Integer, String, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- CONFIGURACIÓN DE BASE DE DATOS (SUPABASE CON POOLER 6543) ---
DATABASE_URL = "postgresql+psycopg2://postgres:matamata675411302603@db.picteudhhdsytfvpvoja.supabase.co:6543/postgres?sslmode=require"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Definición exacta del modelo de la tabla productos en Supabase
class ProductoModel(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    precio = Column(Numeric(10, 2), nullable=False)
    categoria = Column(String, nullable=False)
    descripcion = Column(String)
    imagen = Column(String)

# --- HISTORIAL TEMPORAL PARA POLLING (NOTIFICACIONES) ---
historial_notificaciones = []

# --- LÓGICA DE WEBSOCKETS ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if self.active_connections:
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# --- MODELOS PYDANTIC ---
class ItemPedido(BaseModel):
    nombre: str
    precio: float
    cantidad: Optional[int] = 1

class PedidoRequest(BaseModel):
    mesa: int
    items: List[ItemPedido]
    total: float

class AlertaRequest(BaseModel):
    mesa: int
    tipo: str

# --- RUTAS WEB ---
@app.get("/", response_class=HTMLResponse)
async def ver_menu(request: Request, mesa: int = 1):
    db = SessionLocal()
    menu_lista = []
    try:
        productos_db = db.query(ProductoModel).all()
        menu_lista = [
            {
                "id": p.id,
                "nombre": p.nombre,
                "precio": float(p.precio),
                "categoria": p.categoria,
                "descripcion": p.descripcion,
                "imagen": p.imagen
            } for p in productos_db
        ]
    except Exception as e:
        print("ERROR AL CONSULTAR SUPABASE (INDEX):", e)
    finally:
        db.close()

    categorias = {
        "Bebidas": [p for p in menu_lista if p["categoria"] == "Bebidas"],
        "Comida": [p for p in menu_lista if p["categoria"] == "Comida"],
        "Postres": [p for p in menu_lista if p["categoria"] == "Postres"]
    }
    return templates.TemplateResponse(request=request, name="index.html", context={"mesa": mesa, "categorias": categorias})

@app.get("/admin", response_class=HTMLResponse)
async def ver_admin(request: Request):
    db = SessionLocal()
    menu_lista = []
    try:
        productos_db = db.query(ProductoModel).all()
        menu_lista = [
            {
                "id": p.id,
                "nombre": p.nombre,
                "precio": float(p.precio),
                "categoria": p.categoria,
                "descripcion": p.descripcion,
                "imagen": p.imagen
            } for p in productos_db
        ]
    except Exception as e:
        print("ERROR AL CONSULTAR SUPABASE (ADMIN):", e)
    finally:
        db.close()

    return templates.TemplateResponse(request=request, name="admin.html", context={"productos": menu_lista})

# --- APIS Y POLLING DE ALERTAS ---
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/enviar-pedido")
async def recibir_pedido(pedido: PedidoRequest):
    nuevo_evento = {
        "tipo": "nuevo_pedido", 
        "mesa": pedido.mesa, 
        "items": [i.dict() for i in pedido.items], 
        "total": pedido.total
    }
    historial_notificaciones.append(nuevo_evento)
    await manager.broadcast(nuevo_evento)
    return {"status": "success"}

@app.post("/api/alerta-mesero")
async def alerta_mesero(alerta: AlertaRequest):
    titulo = "🛎️ ¡Llamando al Mesero!" if alerta.tipo == "mesero" else "🧾 ¡Pidiendo la Cuenta!"
    nuevo_evento = {
        "tipo": "alerta", 
        "titulo": titulo, 
        "mesa": alerta.mesa, 
        "mensaje": f"La Mesa #{alerta.mesa} solicita {alerta.tipo}."
    }
    historial_notificaciones.append(nuevo_evento)
    await manager.broadcast(nuevo_evento)
    return {"status": "success"}

@app.get("/api/obtener-eventos")
async def obtener_eventos():
    global historial_notificaciones
    eventos = historial_notificaciones.copy()
    historial_notificaciones.clear()
    return eventos

# --- ADMIN (GESTIÓN EN SUPABASE CON DIAGNÓSTICO) ---
@app.post("/admin/agregar")
async def agregar_producto(
    nombre: str = Form(...), 
    precio: float = Form(...), 
    categoria: str = Form(...), 
    descripcion: str = Form(default=""), 
    imagen_file: UploadFile = File(...)
):
    try:
        # 1. Intentar guardar la imagen localmente
        file_path = os.path.join(UPLOAD_DIR, imagen_file.filename)
        with open(file_path, "wb") as buffer: 
            shutil.copyfileobj(imagen_file.file, buffer)
        
        # 2. Intentar guardar en Supabase
        db = SessionLocal()
        nuevo_producto = ProductoModel(
            nombre=nombre,
            precio=precio,
            categoria=categoria,
            descripcion=descripcion,
            imagen=imagen_file.filename
        )
        db.add(nuevo_producto)
        db.commit()
        db.close()
        
        return RedirectResponse(url="/admin", status_code=303)
        
    except Exception as e:
        # Muestra el error exacto en la interfaz web si algo falla
        return HTMLResponse(content=f"<h2 style='color:red;'>ERROR EXACTO AL GUARDAR:</h2><pre>{str(e)}</pre>", status_code=500)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    db = SessionLocal()
    try:
        producto = db.query(ProductoModel).filter(ProductoModel.id == producto_id).first()
        if producto:
            db.delete(producto)
            db.commit()
    except Exception as e:
        print("ERROR AL ELIMINAR EN SUPABASE:", e)
    finally:
        db.close()

    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
