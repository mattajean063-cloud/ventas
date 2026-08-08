import os
from fastapi import FastAPI, Request, Form, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Set, Optional
import shutil

app = FastAPI()

# --- RUTAS DINÁMICAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- BASE DE DATOS (En memoria) ---
menu_data = [
    {"id": 1, "nombre": "Café Americano Antigüeño", "precio": 15.00, "categoria": "Bebidas", "descripcion": "Café de altura con notas volcánicas.", "imagen": "americano.jpg"},
    {"id": 2, "nombre": "Desayuno Típico Don Nicolás", "precio": 35.00, "categoria": "Comida", "descripcion": "Frijoles, huevos, plátanos y queso.", "imagen": "desayuno.jpg"}
]

# --- HISTORIAL TEMPORAL PARA GARANTIZAR ENTREGA (POLLING) ---
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

# --- MODELOS ---
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
    categorias = {
        "Bebidas": [p for p in menu_data if p["categoria"] == "Bebidas"],
        "Comida": [p for p in menu_data if p["categoria"] == "Comida"],
        "Postres": [p for p in menu_data if p["categoria"] == "Postres"]
    }
    return templates.TemplateResponse(request=request, name="index.html", context={"mesa": mesa, "categorias": categorias})

@app.get("/admin", response_class=HTMLResponse)
async def ver_admin(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={"productos": menu_data})

# --- APIS Y WEBSOCKETS ---
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

# --- ADMIN ---
@app.post("/admin/agregar")
async def agregar_producto(nombre: str = Form(...), precio: float = Form(...), categoria: str = Form(...), descripcion: str = Form(default=""), imagen_file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, imagen_file.filename)
    with open(file_path, "wb") as buffer: shutil.copyfileobj(imagen_file.file, buffer)
    nuevo_id = max([p["id"] for p in menu_data], default=0) + 1
    menu_data.append({"id": nuevo_id, "nombre": nombre, "precio": precio, "categoria": categoria, "descripcion": descripcion, "imagen": imagen_file.filename})
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    global menu_data
    menu_data = [p for p in menu_data if p["id"] != producto_id]
    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
