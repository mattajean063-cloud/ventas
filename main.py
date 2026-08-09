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

EVENTOS_PENDIENTES = []

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
    subcategoria: Optional[str] = ""

class PedidoRequest(BaseModel):
    mesa: int
    items: List[ItemPedido]
    total: float

class AlertaRequest(BaseModel):
    mesa: int
    tipo: str

@app.get("/", response_class=HTMLResponse)
async def ver_menu(request: Request, mesa: int = 1):
    global TURNO_ACTUAL_SISTEMA
    menu_lista = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200: menu_lista = response.json()
    except Exception as e: print("ERROR SUPABASE (INDEX):", e)

    productos_filtrados = []
    for p in menu_lista:
        categoria = p.get("categoria")
        horario = p.get("horario", "Ambos")
        if categoria == "Comida":
            if horario == "Ambos" or horario == TURNO_ACTUAL_SISTEMA: productos_filtrados.append(p)
        else: productos_filtrados.append(p)

    categorias = {
        "Bebidas Frías": [p for p in productos_filtrados if p.get("categoria") == "Bebidas Frías"],
        "Bebidas Calientes": [p for p in productos_filtrados if p.get("categoria") == "Bebidas Calientes"],
        "Métodos": [p for p in productos_filtrados if p.get("categoria") == "Métodos"],
        "Comida": [p for p in productos_filtrados if p.get("categoria") == "Comida"],
        "Postres": [p for p in productos_filtrados if p.get("categoria") == "Postres"],
        "Cócteles y Café Filtrado": [p for p in productos_filtrados if p.get("categoria") == "Cócteles y Café Filtrado"],
        "Extras": [p for p in productos_filtrados if p.get("categoria") == "Extras"]
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

@app.post("/admin/cambiar-turno")
async def cambiar_turno(turno: str = Form(...)):
    global TURNO_ACTUAL_SISTEMA
    if turno in ["Mañana", "Tarde"]: TURNO_ACTUAL_SISTEMA = turno
    return RedirectResponse(url="/admin", status_code=303)

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
async def agregar_producto(request: Request):
    try:
        form_data = await request.form()
        nombre = form_data.get("nombre")
        precio = float(form_data.get("precio", 0))
        categoria = form_data.get("categoria")
        descripcion = form_data.get("descripcion", "")
        horario = form_data.get("horario", "Ambos")
        config_tamano = form_data.get("config_tamano", "ninguno")
        subcategorias = form_data.get("subcategorias", "")
        
        admite_promo = True if form_data.get("admite_promo") in ["true", "on", True] else False
        admite_extras_cafe = True if form_data.get("admite_extras_cafe") in ["true", "on", True] else False
        
        imagen_file = form_data.get("imagen_file")
        imagen_base64 = ""
        if imagen_file and hasattr(imagen_file, "filename") and imagen_file.filename:
            file_bytes = await imagen_file.read()
            if file_bytes:
                encoded_image = base64.b64encode(file_bytes).decode('utf-8')
                content_type = imagen_file.content_type or "image/jpeg"
                imagen_base64 = f"data:{content_type};base64,{encoded_image}"

        payload = {
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "descripcion": descripcion,
            "horario": horario if categoria == "Comida" else "Ambos",
            "config_tamano": config_tamano,
            "subcategorias": subcategorias,
            "admite_promo": admite_promo,
            "admite_extras_cafe": admite_extras_cafe,
            "imagen": imagen_base64
        }
        
        db_headers = {
            **HEADERS, 
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        res = requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=payload)
        print("STATUS SUPABASE:", res.status_code)
        print("RESPUESTA SUPABASE:", res.text)
    except Exception as e:
        print("EXCEPCIÓN EN /admin/agregar:", e)
    
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-imagen/{producto_id}")
async def actualizar_imagen(producto_id: int, imagen_file: UploadFile = File(...)):
    try:
        file_bytes = await imagen_file.read()
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
        content_type = imagen_file.content_type or "image/jpeg"
        imagen_base64 = f"data:{content_type};base64,{encoded_image}"
        
        payload = {"imagen": imagen_base64}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: print("ERROR AL ACTUALIZAR IMAGEN:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-precio/{producto_id}")
async def actualizar_precio(producto_id: int, nuevo_precio: float = Form(...)):
    try:
        payload = {"precio": float(nuevo_precio)}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: print("ERROR:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-subcategorias/{producto_id}")
async def actualizar_subcategorias(producto_id: int, subcategorias: str = Form(default="")):
    try:
        payload = {"subcategorias": subcategorias}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: print("ERROR AL ACTUALIZAR SUBCATEGORIAS:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-horario/{producto_id}")
async def actualizar_horario(producto_id: int, horario: str = Form(...)):
    try:
        payload = {"horario": horario}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: print("ERROR:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-tamano/{producto_id}")
async def actualizar_tamano(producto_id: int, config_tamano: str = Form(...)):
    try:
        payload = {"config_tamano": config_tamano}
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=db_headers, json=payload)
    except Exception as e: 
        print("ERROR AL ACTUALIZAR TAMAÑO:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    try: requests.delete(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS)
    except Exception as e: print("ERROR:", e)
    return RedirectResponse(url="/admin", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
