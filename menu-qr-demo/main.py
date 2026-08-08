import os
from fastapi import FastAPI, Request, Form, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Set
import shutil

app = FastAPI()

# Rutas absolutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- (Base de datos y lógica igual que antes) ---
menu_data = [
    {"id": 1, "nombre": "Café Americano Antigüeño", "precio": 15.00, "categoria": "Bebidas", "descripcion": "Café de altura con notas volcánicas.", "imagen": "americano.jpg"},
    {"id": 2, "nombre": "Desayuno Típico Don Nicolás", "precio": 35.00, "categoria": "Comida", "descripcion": "Frijoles, huevos, plátanos y queso.", "imagen": "desayuno.jpg"}
]

class ConnectionManager:
    def __init__(self): self.active_connections: Set[WebSocket] = set()
    async def connect(self, ws: WebSocket): await ws.accept(); self.active_connections.add(ws)
    def disconnect(self, ws: WebSocket): self.active_connections.remove(ws)
    async def broadcast(self, msg: dict): 
        for conn in self.active_connections: await conn.send_json(msg)

manager = ConnectionManager()

# ... (Tus rutas @app.get, @app.post, etc. se mantienen igual) ...

if __name__ == "__main__":
    import uvicorn
    # Puerto dinámico para Render
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
