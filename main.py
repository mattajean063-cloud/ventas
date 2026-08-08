import base64
import json
import os
import requests
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import jinja2

# Activamos debug=True para ver errores detallados si ocurren
app = FastAPI(debug=True)

# Inicialización segura de plantillas sin conflicto de caché
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True
)
templates = Jinja2Templates(env=env)

# Configuración de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tu-proyecto.supabase.co")
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

# Variable global para el turno actual
turno_global = "Mañana"

@app.get("/admin", response_class=HTMLResponse)
async def panel_admin(request: Request):
    productos = []
    try:
        response = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=*", headers=HEADERS)
        if response.status_code == 200:
            productos = response.json()
        else:
            print("Error de Supabase en /admin:", response.text)
    except Exception as e:
        print("Error obteniendo productos:", e)
    
    # Renderizado nativo con Jinja2 para evitar conflictos de caché con Starlette
    template = env.get_template("admin.html")
    html_content = template.render(
        request=request,
        productos=productos,
        turno_actual=turno_global
    )
    return HTMLResponse(content=html_content)

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

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/disparar-alerta")
async def disparar_alerta(evento: dict):
    await manager.broadcast(evento)
    return {"status": "enviado"}
