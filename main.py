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

SUPABASE_URL = "https://picteudhhdsytfvpvoja.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpY3RldWRoaGRzeXRmdnB2b2phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNTM4NDYsImV4cCI6MjEwMTcyOTg0Nn0.g5FWFDX3Ks6189MpJ98YXMJy2-L3GHbhZkSgdKldHVE" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Prefer": "return=representation"
}

historial_notificaciones = []
TURNO_ACTUAL_SISTEMA = "Mañana"

# Menú precargado completo con los datos del PDF e imágenes
MENU_INICIAL_COMPLETO = [
    {"nombre": "Chilaquiles", "precio": 55.0, "categoria": "Comida", "descripcion": "Huevos estrellados sobre tortillas fritas, salsa roja, queso mozzarella, crema, pechuga de pollo y cebolla morada curtida.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400"},
    {"nombre": "Waffle Americano", "precio": 55.0, "categoria": "Comida", "descripcion": "Waffle acompañado de 2 huevos fritos, tiras de tocino, fruta y miel maple.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1562376552-0d160a2f238d?w=400"},
    {"nombre": "Omelette de Claras", "precio": 50.0, "categoria": "Comida", "descripcion": "Relleno de queso mozzarella, espinaca, tomate, chile pimiento, cebolla, papas country, yogurt natural, granola, miel maple y fruta.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=400"},
    {"nombre": "Omelette Americano", "precio": 35.0, "categoria": "Comida", "descripcion": "Relleno con jamón y queso mozzarella, salsa roja, pan tostado con queso crema, granola y jalea.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=400"},
    {"nombre": "Huevos Ahogados", "precio": 40.0, "categoria": "Comida", "descripcion": "Huevos en salsa roja con chorizo, frijoles volteados y pan tostado con mantequilla de ajo.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=400"},
    {"nombre": "Típico", "precio": 40.0, "categoria": "Comida", "descripcion": "Huevos al gusto, frijoles volteados, queso, crema, salsa roja, plátanos fritos y tortillas.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=400"},
    {"nombre": "Avocado Toast", "precio": 25.0, "categoria": "Comida", "descripcion": "Pan de molde tostado con aderezo de cilantro, aguacate y huevo revuelto con pimienta.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1588137378633-dea1336ce1e2?w=400"},
    {"nombre": "Waffle Dulce", "precio": 45.0, "categoria": "Postres", "descripcion": "Waffle acompañado de una bola de helado y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=400"},
    {"nombre": "Tostadas a la Francesa", "precio": 35.0, "categoria": "Postres", "descripcion": "Pan remojado en canela y leche, relleno de queso ricota con mermelada de fresas y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1484723091739-30a097e8f929?w=400"},
    {"nombre": "Parfait", "precio": 40.0, "categoria": "Postres", "descripcion": "Yogurt natural sin azúcar acompañado de granola, miel maple y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400"},
    {"nombre": "La Tablita (8 tacos - 4 carnes)", "precio": 80.0, "categoria": "Comida", "descripcion": "8 tacos con cebolla, cilantro, salsas de la casa y limón (4 carnes).", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400"},
    {"nombre": "La Tablita (8 tacos - Cochinita Pibil)", "precio": 85.0, "categoria": "Comida", "descripcion": "8 tacos de cochinita pibil con cebolla, cilantro y salsas.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=400"},
    {"nombre": "La Tablita (8 tacos - Quesillo y Chorizo)", "precio": 85.0, "categoria": "Comida", "descripcion": "8 tacos de quesillo y chorizo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400"},
    {"nombre": "La Tablita (8 tacos - Pollo Maracuyá)", "precio": 80.0, "categoria": "Comida", "descripcion": "8 tacos de pollo con salsa de maracuyá.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1613514785940-daed07799d9b?w=400"},
    {"nombre": "Baguette 4 Carnes", "precio": 55.0, "categoria": "Comida", "descripcion": "Cerdo, res, pollo, salchicha, mozzarella, salsa de aguacate, tomate, lechuga y cebolla curtida.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400"},
    {"nombre": "Baguette de Pollo", "precio": 45.0, "categoria": "Comida", "descripcion": "Filete de pollo a la plancha, salsa de aguacate, lechuga, chile pimiento, cebolla y tomate.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400"},
    {"nombre": "Espresso", "precio": 10.0, "categoria": "Bebidas Calientes", "descripcion": "Espresso tradicional de 1 oz.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=400"},
    {"nombre": "Cappuccino", "precio": 17.0, "categoria": "Bebidas Calientes", "descripcion": "Cappuccino clásico.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"},
    {"nombre": "Latte", "precio": 25.0, "categoria": "Bebidas Calientes", "descripcion": "Disponible en caliente o frío (12oz / 16oz).", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=400"}
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
        res = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=id", headers=HEADERS)
        if res.status_code == 200:
            productos_actuales = res.json()
            print(f"Estado actual en Supabase: {len(productos_actuales)} productos encontrados.")
            if len(productos_actuales) == 0:
                db_headers = {**HEADERS, "Content-Type": "application/json"}
                for prod in MENU_INICIAL_COMPLETO:
                    r = requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=prod)
                    if r.status_code not in [200, 201]:
                        print(f"❌ Error al insertar '{prod['nombre']}': {r.status_code} - {r.text}")
                print("¡Proceso de precarga finalizado!")
        else:
            print(f"❌ Error al conectar con Supabase (GET): {res.status_code} - {res.text}")
    except Exception as e:
        print("❌ Excepción crítica en startup_event:", e)

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
        while True: await websocket.receive_text()
    except WebSocketDisconnect: manager.disconnect(websocket)

@app.post("/api/enviar-pedido")
async def recibir_pedido(pedido: PedidoRequest):
    nuevo_evento = {"tipo": "nuevo_pedido", "mesa": pedido.mesa, "items": [i.dict() for i in pedido.items], "total": pedido.total}
    historial_notificaciones.append(nuevo_evento)
    await manager.broadcast(nuevo_evento)
    return {"status": "success"}

@app.post("/api/alerta-mesero")
async def alerta_mesero(alerta: AlertaRequest):
    titulo = "🛎️ ¡Llamando al Mesero!" if alerta.tipo == "mesero" else "🧾 ¡Pidiendo la Cuenta!"
    nuevo_evento = {"tipo": "alerta", "titulo": titulo, "mesa": alerta.mesa, "mensaje": f"La Mesa #{alerta.mesa} solicita {alerta.tipo}."}
    historial_notificaciones.append(nuevo_evento)
    await manager.broadcast(nuevo_evento)
    return {"status": "success"}

@app.get("/api/obtener-eventos")
async def obtener_eventos():
    global historial_notificaciones
    eventos = historial_notificaciones.copy()
    historial_notificaciones.clear()
    return eventos

@app.post("/admin/agregar")
async def agregar_producto(
    nombre: str = Form(...), 
    precio: float = Form(...), 
    categoria: str = Form(...), 
    descripcion: str = Form(default=""), 
    horario: str = Form(default="Ambos"), 
    config_tamano: str = Form(default="ninguno"),
    admite_promo: Optional[str] = Form(default=None),
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
            "horario": horario if categoria == "Comida" else "Ambos",
            "config_tamano": config_tamano,
            "admite_promo": True if admite_promo == "true" else False,
            "imagen": imagen_base64
        }
        db_headers = {**HEADERS, "Content-Type": "application/json"}
        r = requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=payload)
        print("Respuesta de inserción:", r.status_code, r.text)
    except Exception as e: print("ERROR EN /admin/agregar:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-imagen/{producto_id}")
async def actualizar_imagen(producto_id: int, nueva_imagen_file: UploadFile = File(...)):
    try:
        file_bytes = await nueva_imagen_file.read()
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
        content_type = nueva_imagen_file.content_type or "image/jpeg"
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

@app.post("/admin/actualizar-horario/{producto_id}")
async def actualizar_horario(producto_id: int, horario: str = Form(...)):
    try:
        payload = {"horario": horario}
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
