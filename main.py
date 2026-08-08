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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ⚠️ CREDENCIALES DE SUPABASE
SUPABASE_URL = "https://picteudhhdsytfvpvoja.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpY3RldWRoaGRzeXRmdnB2b2phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNTM4NDYsImV4cCI6MjEwMTcyOTg0Nn0.g5FWFDX3Ks6189MpJ98YXMJy2-L3GHbhZkSgdKldHVE" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Prefer": "return=representation"
}

TURNO_ACTUAL_SISTEMA = "Mañana"

# 🧠 COLA DE EVENTOS PENDIENTES PARA EL RESPALDO HÍBRIDO (WEBHOOK/HTTP)
EVENTOS_PENDIENTES = []

MENU_INICIAL_COMPLETO = [
    {"nombre": "Chilaquiles", "precio": 55.0, "categoria": "Comida", "descripcion": "Huevos estrellados sobre tortillas fritas, salsa roja, queso mozzarella, crema, pechuga de pollo y cebolla morada curtida.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "admite_extras_cafe": False, "imagen": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400"},
    {"nombre": "Waffle Americano", "precio": 55.0, "categoria": "Comida", "descripcion": "Waffle acompañado de 2 huevos fritos, tiras de tocino, fruta y miel maple.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "admite_extras_cafe": False, "imagen": "https://images.unsplash.com/photo-1562376552-0d160a2f238d?w=400"},
    {"nombre": "Espresso", "precio": 10.0, "categoria": "Bebidas Calientes", "descripcion": "Espresso tradicional de 1 oz.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "admite_extras_cafe": True, "imagen": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=400"},
    {"nombre": "Americano", "precio": 13.0, "categoria": "Bebidas Calientes", "descripcion": "Americano 8oz / 12oz.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "admite_extras_cafe": True, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"}
]

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    async def broadcast(self, message: dict):
        EVENTOS_PENDIENTES.append(message)
        if self.active_connections:
            for connection in self.active_connections:
                try: await connection.send_json(message)
                except: pass

manager = ConnectionManager()

class ItemPedido(BaseModel):
    nombre: str
    precio: float
    cantidad: Optional[int] = 1
    cliente: Optional[str] = "General"
    tipoLeche: Optional[str] = ""
    tipoEndulzante: Optional[str] = ""
    tamano: Optional[str] = ""
    promo: Optional[str] = ""
    nota: Optional[str] = ""

class PedidoRequest(BaseModel):
    mesa: int
    items: List[ItemPedido]
    total: float

class AlertaRequest(BaseModel):
    mesa: int
    tipo: str

@app.on_event("startup")
async def startup_event():
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=nombre", headers=HEADERS)
        if res.status_code == 200:
            existentes = {p["nombre"] for p in res.json()}
            db_headers = {**HEADERS, "Content-Type": "application/json"}
            
            for prod in MENU_INICIAL_COMPLETO:
                if prod["nombre"] not in existentes:
                    requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=prod)
    except Exception as e:
        print("Error en startup_event:", e)

@app.get("/", response_class=HTMLResponse)
async def ver_menu(request: Request, mesa: int = 1):
    global TURNO_ACTUAL_SISTEMA
    menu_lista = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200: menu_lista = response.json()
    except Exception as e: print("ERROR SUPABASE (INDEX):", e)

    categorias = {
        "Comida": [p for p in menu_lista if p.get("categoria") == "Comida"],
        "Postres": [p for p in menu_lista if p.get("categoria") == "Postres"],
        "Bebidas Calientes": [p for p in menu_lista if p.get("categoria") == "Bebidas Calientes"],
        "Bebidas Frías": [p for p in menu_lista if p.get("categoria") == "Bebidas Frías"]
    }
    nombre_menu = "Menú Brunch" if TURNO_ACTUAL_SISTEMA == "Mañana" else "Menú de Tarde"
    return templates.TemplateResponse(request=request, name="index.html", context={"mesa": mesa, "categorias": categorias, "turno": TURNO_ACTUAL_SISTEMA, "nombre_menu": nombre_menu})

@app.get("/admin", response_class=HTMLResponse)
async def ver_admin(request: Request):
    global TURNO_ACTUAL_SISTEMA
    menu_lista = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200: menu_lista = response.json()
    except Exception as e: print("ERROR SUPABASE (ADMIN):", e)
    return templates.TemplateResponse(request=request, name="admin.html", context={"productos": menu_lista, "turno_actual": TURNO_ACTUAL_SISTEMA})

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
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
    await manager.broadcast(nuevo_evento)
    return {"status": "success"}

@app.get("/api/obtener-eventos")
async def obtener_eventos():
    global EVENTOS_PENDIENTES
    eventos_a_enviar = EVENTOS_PENDIENTES.copy()
    EVENTOS_PENDIENTES.clear()
    return eventos_a_enviar

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
            "horario": "Ambos",
            "config_tamano": "ninguno",
            "admite_promo": False,
            "admite_extras_cafe": False,
            "imagen": imagen_base64
        }
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=payload)
    except Exception as e: print("ERROR EN /admin/agregar:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-precio/{producto_id}")
async def actualizar_precio(producto_id: int, nuevo_precio: float = Form(...)):
    try:
        payload = {"precio": float(nuevo_precio)}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: print("ERROR:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    try: requests.delete(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS)
    except Exception as e: print("ERROR:", e)
    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
