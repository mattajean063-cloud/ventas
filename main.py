import base64
import json
import os
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Configuración de plantillas (asegurate de tener una carpeta llamada 'templates')
templates = Jinja2Templates(directory="templates")

# Configuración de Supabase (ajusta tus credenciales o variables de entorno)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://picteudhhdsytfvpvoja.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpY3RldWRoaGRzeXRmdnB2b2phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNTM4NDYsImV4cCI6MjEwMTcyOTg0Nn0.g5FWFDX3Ks6189MpJ98YXMJy2-L3GHbhZkSgdKldHVE")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Gestor de conexiones para WebSockets (Notificaciones en tiempo real)
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# Variable global para el turno actual ('Mañana' o 'Tarde')
turno_global = "Mañana"

@app.get("/admin", response_class=HTMLResponse)
async def panel_admin(request: Request):
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        productos = response.json() if response.status_code == 200 else []
    except Exception:
        productos = []
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "productos": productos,
        "turno_actual": turno_global
    })

@app.post("/admin/cambiar-turno")
async def cambiar_turno(turno: str = Form(...)):
    global turno_global
    turno_global = turno
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/agregar")
async def agregar_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...),
    horario: str = Form(...),
    config_tamano: str = Form(...),
    admite_promo: str = Form(None),
    descripcion: str = Form(...),
    imagen_file: UploadFile = File(...)
):
    try:
        file_bytes = await imagen_file.read()
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
        content_type = imagen_file.content_type or "image/jpeg"
        imagen_base64 = f"data:{content_type};base64,{encoded_image}"

        payload = {
            "nombre": nombre,
            "precio": precio,
            "categoria": categoria,
            "horario": horario,
            "config_tamano": config_tamano,
            "admite_promo": True if admite_promo else False,
            "descripcion": descripcion,
            "imagen": imagen_base64
        }
        requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=HEADERS, json=payload)
    except Exception as e:
        print("Error al agregar producto:", e)
        
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-precio/{producto_id}")
async def actualizar_precio(producto_id: int, nuevo_precio: float = Form(...)):
    try:
        payload = {"precio": nuevo_precio}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS, json=payload)
    except Exception as e:
        print("Error al actualizar precio:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-horario/{producto_id}")
async def actualizar_horario(producto_id: int, horario: str = Form(...)):
    try:
        payload = {"horario": horario}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS, json=payload)
    except Exception as e:
        print("Error al actualizar horario:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/actualizar-imagen/{producto_id}")
async def actualizar_imagen(producto_id: int, imagen_file: UploadFile = File(...)):
    try:
        file_bytes = await imagen_file.read()
        encoded_image = base64.b64encode(file_bytes).decode('utf-8')
        content_type = imagen_file.content_type or "image/jpeg"
        imagen_base64 = f"data:{content_type};base64,{encoded_image}"
        
        payload = {"imagen": imagen_base64}
        requests.patch(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS, json=payload)
    except Exception as e:
        print("ERROR EN /admin/actualizar-imagen:", e)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/eliminar/{producto_id}")
async def eliminar_producto(producto_id: int):
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/productos?id=eq.{producto_id}", headers=HEADERS)
    except Exception as e:
        print("Error al eliminar producto:", e)
    return RedirectResponse(url="/admin", status_code=303)

# Ruta WebSocket para recibir y mandar eventos al panel admin en tiempo real
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Puedes recibir mensajes de prueba o comandos si lo requieres
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Endpoint opcional para disparar notificaciones desde otros puntos de la app hacia el admin
@app.post("/api/disparar-alerta")
async def disparar_alerta(evento: dict):
    await manager.broadcast(evento)
    return {"status": "enviado"}
