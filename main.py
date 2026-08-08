import os
import base64
from fastapi import FastAPI, Request, Form, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Set, Optional
import requests

app = FastAPI()

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- CREDENCIALES DE LA API REST DE SUPABASE ---
SUPABASE_URL = "https://picteudhhdsytfvpvoja.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpY3RldWRoaGRzeXRmdnB2b2phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNTM4NDYsImV4cCI6MjEwMTcyOTg0Nn0.g5FWFDX3Ks6189MpJ98YXMJy2-L3GHbhZkSgdKldHVE" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Prefer": "return=representation"
}

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
    menu_lista = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200:
            menu_lista = response.json()
    except Exception as e:
        print("ERROR AL CONSULTAR SUPABASE API (INDEX):", e)

    categorias = {
        "Bebidas": [p for p in menu_lista if p.get("categoria") == "Bebidas"],
        "Comida": [p for p in menu_lista if p.get("categoria") == "Comida"],
        "Postres": [p for p in menu_lista if p.get("categoria") == "Postres"]
    }
    return templates.TemplateResponse(request=request, name="index.html", context={"mesa": mesa, "categorias": categorias})

@app.get("/admin", response_class=HTMLResponse)
async def ver_admin(request: Request):
    menu_lista = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200:
            menu_lista = response.json()
    except Exception as e:
        print("ERROR AL CONSULTAR SUPABASE API (ADMIN):", e)

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

# --- ADMIN (GESTIÓN DE PRODUCTOS CON IMAGEN BASE64) ---
@app.post("/admin/agregar")
async def agregar_producto(
    nombre: str = Form(...), 
    precio: float = Form(...), 
    categoria: str = Form(...), 
    descripcion: str = Form(default=""), 
    imagen_file: UploadFile = File(...)
):
    try:
        file_bytes = await imagen_file.read()
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
        content_type = imagen_file.content_type or "image/jpeg"
        imagen_base64 = f"data:{content_type};base64,{encoded_image}"
        
        payload = {
            "nombre": nombre,
            "precio": float(precio),
            "categoria": categoria,
            "descripcion": descripcion,
            "imagen": imagen_base64
        }
        
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=payload)
        
    except Exception as e:
        print("ERROR GENERAL EN /admin/agregar:", e)

    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-precio/{producto_id}")
async def actualizar_precio(producto_id: int, nuevo_precio: float = Form(...)):
    try:
        payload = {
            "precio": float(nuevo_precio)
        }
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e:
        print("ERROR AL ACTUALIZAR PRECIO EN SUPABASE:", e)

    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS)
    except Exception as e:
        print("ERROR AL ELIMINAR EN SUPABASE API:", e)

    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
