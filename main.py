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

# ⚠️ REEMPLAZA CON TU LLAVE REAL DE SUPABASE (anon / public)
SUPABASE_URL = "https://picteudhhdsytfvpvoja.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpY3RldWRoaGRzeXRmdnB2b2phIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODYxNTM4NDYsImV4cCI6MjEwMTcyOTg0Nn0.g5FWFDX3Ks6189MpJ98YXMJy2-L3GHbhZkSgdKldHVE" 

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Prefer": "return=representation"
}

historial_notificaciones = []
TURNO_ACTUAL_SISTEMA = "Mañana"

# --- MENÚ COMPLETO Y EXACTO (CON APARTADO DE MÉTODOS) ---
MENU_INICIAL_COMPLETO = [
    # 1. Menú Brunch / Salados (Mañana - Incluyen opción de bebida)
    {"nombre": "Chilaquiles", "precio": 55.0, "categoria": "Comida", "descripcion": "Huevos estrellados sobre tortillas fritas, salsa roja, queso mozzarella, crema, pechuga de pollo y cebolla morada curtida.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400"},
    {"nombre": "Waffle Americano", "precio": 55.0, "categoria": "Comida", "descripcion": "Waffle acompañado de 2 huevos fritos, tiras de tocino, fruta y miel maple.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1562376552-0d160a2f238d?w=400"},
    {"nombre": "Omelette de Claras", "precio": 50.0, "categoria": "Comida", "descripcion": "Relleno de queso mozzarella, espinaca, tomate, chile pimiento, cebolla, papas country, yogurt natural, granola, miel maple y fruta.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1510693206972-df098062cb71?w=400"},
    {"nombre": "Omelette Americano", "precio": 35.0, "categoria": "Comida", "descripcion": "Relleno con jamón y queso mozzarella, salsa roja, pan tostado con queso crema, granola y jalea.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=400"},
    {"nombre": "Huevos Ahogados", "precio": 40.0, "categoria": "Comida", "descripcion": "Huevos ahogados en salsa roja con chorizo, frijoles volteados y pan tostado con mantequilla de ajo.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1482049016688-2d3e1b311543?w=400"},
    {"nombre": "Típico", "precio": 40.0, "categoria": "Comida", "descripcion": "Huevos al gusto, frijoles volteados, queso, crema, salsa roja, plátanos fritos y tortillas.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1533089860892-a7c6f0a88666?w=400"},
    {"nombre": "Avocado Toast", "precio": 25.0, "categoria": "Comida", "descripcion": "Pan de molde tostado con aderezo de cilantro, aguacate y huevo revuelto con pimienta.", "horario": "Mañana", "config_tamano": "ninguno", "admite_promo": True, "imagen": "https://images.unsplash.com/photo-1588137378633-dea1336ce1e2?w=400"},

    # 2. Dulces y Postres Brunch
    {"nombre": "Waffle Dulce", "precio": 45.0, "categoria": "Postres", "descripcion": "Waffle acompañado de una bola de helado y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=400"},
    {"nombre": "Tostadas a la Francesa", "precio": 35.0, "categoria": "Postres", "descripcion": "2 rebanadas de pan remojadas en canela y leche, relleno de queso ricota con mermelada de fresas y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1484723091739-30a097e8f929?w=400"},
    {"nombre": "Parfait", "precio": 40.0, "categoria": "Postres", "descripcion": "Yogurt natural sin azúcar acompañado de granola, miel maple y fruta.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400"},

    # 3. Tacos y Antojitos
    {"nombre": "La Tablita (8 tacos - 4 carnes)", "precio": 80.0, "categoria": "Comida", "descripcion": "8 tacos con cebolla, cilantro, salsas de la casa y limón.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400"},
    {"nombre": "La Tablita (8 tacos - Cochinita Pibil)", "precio": 85.0, "categoria": "Comida", "descripcion": "8 tacos de cochinita pibil con cebolla, cilantro y salsas.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=400"},
    {"nombre": "La Tablita (8 tacos - Quesillo y Chorizo)", "precio": 85.0, "categoria": "Comida", "descripcion": "8 tacos de quesillo y chorizo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400"},
    {"nombre": "La Tablita (8 tacos - Pollo con salsa de maracuyá)", "precio": 80.0, "categoria": "Comida", "descripcion": "8 tacos de pollo con salsa de maracuyá.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1613514785940-daed07799d9b?w=400"},
    {"nombre": "La Tablita (Mixtos - 2 opciones)", "precio": 80.0, "categoria": "Comida", "descripcion": "8 tacos combinados con 2 opciones a elegir.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400"},
    
    {"nombre": "La Media Tablita (4 tacos - 4 carnes)", "precio": 43.0, "categoria": "Comida", "descripcion": "4 tacos surtidos con cebolla, cilantro y salsas.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400"},
    {"nombre": "La Media Tablita (4 tacos - Cochinita pibil)", "precio": 45.0, "categoria": "Comida", "descripcion": "4 tacos de cochinita pibil.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=400"},
    {"nombre": "La Media Tablita (4 tacos - Quesillo y chorizo)", "precio": 45.0, "categoria": "Comida", "descripcion": "4 tacos de quesillo y chorizo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400"},
    {"nombre": "La Media Tablita (4 tacos - Pollo con salsa de maracuyá)", "precio": 43.0, "categoria": "Comida", "descripcion": "4 tacos de pollo con salsa de maracuyá.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1613514785940-daed07799d9b?w=400"},
    {"nombre": "La Media Tablita (Mixtos - 2 opciones)", "precio": 45.0, "categoria": "Comida", "descripcion": "4 tacos combinados con 2 opciones a elegir.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=400"},

    # 4. Sandwiches y Baguettes
    {"nombre": "Baguette 4 Carnes", "precio": 55.0, "categoria": "Comida", "descripcion": "Cerdo, res, pollo, salchicha, mozzarella, salsa de aguacate, tomate, lechuga y cebolla curtida.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1509722747041-616f39b57569?w=400"},
    {"nombre": "Baguette de Pollo", "precio": 45.0, "categoria": "Comida", "descripcion": "Filete de pollo a la plancha, salsa de aguacate, lechuga, chile pimiento verde, cebolla y tomate.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?w=400"},
    {"nombre": "Baguette Virginia", "precio": 40.0, "categoria": "Comida", "descripcion": "Jamón virginia, queso crema, rodaja de queso amarillo, salsa de aguacate, tomate y lechuga.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1550547660-d9450f859349?w=400"},
    {"nombre": "Sándwich Croque", "precio": 30.0, "categoria": "Comida", "descripcion": "2 rodajas de pan relleno con salsa bechamel, queso mozzarella, frijol o jamón, huevo estrellado y salsa de queso.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1521305916504-4a1121188589?w=400"},
    {"nombre": "Panito", "precio": 20.0, "categoria": "Comida", "descripcion": "Pan de agua relleno de huevos revueltos con chorizo y bañado en queso mozzarella.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1539252554453-80ab65ce3586?w=400"},

    # 5. Muffins
    {"nombre": "Muffin Tocino, Huevo y Queso Amarillo", "precio": 25.0, "categoria": "Comida", "descripcion": "Muffin con tocino, huevo y queso amarillo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?w=400"},
    {"nombre": "Muffin Jamón, Huevo y Queso Amarillo", "precio": 20.0, "categoria": "Comida", "descripcion": "Muffin con jamón, huevo y queso amarillo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1608039829572-78524f79c4c7?w=400"},
    {"nombre": "Muffin Chorizo y Queso Mozzarella", "precio": 22.0, "categoria": "Comida", "descripcion": "Muffin con chorizo y queso mozzarella.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=400"},

    # 6. Antojitos y Compartir (Tarde)
    {"nombre": "Papas con Queso (Mediano)", "precio": 25.0, "categoria": "Comida", "descripcion": "Papas fritas bañadas en salsa de queso cheddar.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400"},
    {"nombre": "Papas con Queso (Grande)", "precio": 45.0, "categoria": "Comida", "descripcion": "Papas fritas bañadas en salsa de queso cheddar.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400"},
    {"nombre": "Nachos Locos (Mediano)", "precio": 28.0, "categoria": "Comida", "descripcion": "Bañados en queso cheddar, chipotle, cilantro, chilli beans, pico de gallo, cebolla, queso fresco y crema.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=400"},
    {"nombre": "Nachos Locos (Grande)", "precio": 50.0, "categoria": "Comida", "descripcion": "Bañados en queso cheddar, chipotle, cilantro, chilli beans, pico de gallo, cebolla, queso fresco y crema.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?w=400"},
    {"nombre": "Papas Locas (Mediano)", "precio": 28.0, "categoria": "Comida", "descripcion": "Papas con cheddar, chipotle, cilantro, chilli beans, pico de gallo, cebolla, queso fresco y crema.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1585109649139-366815a0d713?w=400"},
    {"nombre": "Papas Locas (Grande)", "precio": 50.0, "categoria": "Comida", "descripcion": "Papas con cheddar, chipotle, cilantro, chilli beans, pico de gallo, cebolla, queso fresco y crema.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1585109649139-366815a0d713?w=400"},
    {"nombre": "Plátanos Fritos", "precio": 18.0, "categoria": "Comida", "descripcion": "Porción de plátanos fritos acompañados de crema.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1600891964599-f61ba0e24092?w=400"},
    {"nombre": "Dobladitas Fritas", "precio": 25.0, "categoria": "Comida", "descripcion": "3 tortillas fritas con chorizo y mozzarella, bañadas en salsa verde, mayonesa, cilantro y queso fresco.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1615870216519-2f9fa575fa5c?w=400"},
    {"nombre": "Tostadas (Medio combo - 2)", "precio": 15.0, "categoria": "Comida", "descripcion": "Tostadas fritas con frijol o aguacate, decoradas con salsa y queso.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=400"},
    {"nombre": "Tostadas (Combo - 4)", "precio": 25.0, "categoria": "Comida", "descripcion": "Tostadas fritas con frijol o aguacate, decoradas con salsa y queso.", "horario": "Tarde", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1541544741938-0af808871cc0?w=400"},

    # 7. Postres y Waffles (Tarde)
    {"nombre": "Waffles con Nutella", "precio": 40.0, "categoria": "Postres", "descripcion": "Waffles tradicionales cubiertos de Nutella.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1562376552-0d160a2f238d?w=400"},
    {"nombre": "Waffles con Dulce de Leche", "precio": 40.0, "categoria": "Postres", "descripcion": "Waffles cubiertos con dulce de leche.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=400"},
    {"nombre": "Waffles con Helado y Fruta", "precio": 45.0, "categoria": "Postres", "descripcion": "Waffles acompañados de helado y fruta fresca.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1587314168485-3236d6710814?w=400"},
    {"nombre": "Galleta Chispas Rellena de Nutella", "precio": 12.0, "categoria": "Postres", "descripcion": "Galleta con chispas de chocolate rellena de Nutella.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=400"},
    {"nombre": "Galleta Red Velvet Rellena de Queso Crema", "precio": 15.0, "categoria": "Postres", "descripcion": "Galleta Red Velvet rellena de queso crema.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400"},
    {"nombre": "Galleta Almendras Rellena de Dulce de Leche", "precio": 10.0, "categoria": "Postres", "descripcion": "Galleta de almendras rellena de dulce de leche.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=400"},
    {"nombre": "Galleta Chispas de Chocolate", "precio": 10.0, "categoria": "Postres", "descripcion": "Galleta clásica con chispas de chocolate.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=400"},
    {"nombre": "Brownie", "precio": 20.0, "categoria": "Postres", "descripcion": "Brownie de chocolate casero.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400"},
    {"nombre": "Affogato", "precio": 20.0, "categoria": "Postres", "descripcion": "Bola de helado con espresso.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1594998893017-36147cff1644?w=400"},
    {"nombre": "Nutella Affogato", "precio": 25.0, "categoria": "Postres", "descripcion": "Affogato con toque de Nutella.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1594998893017-36147cff1644?w=400"},
    {"nombre": "Flan con Caramelo", "precio": 25.0, "categoria": "Postres", "descripcion": "Flan tradicional bañado en caramelo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400"},
    {"nombre": "Alfajores", "precio": 30.0, "categoria": "Postres", "descripcion": "Alfajores tradicionales.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400"},
    {"nombre": "Cheesecake", "precio": 20.0, "categoria": "Postres", "descripcion": "Porción de cheesecake tradicional.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=400"},
    {"nombre": "Cheesecake Banano", "precio": 20.0, "categoria": "Postres", "descripcion": "Porción de cheesecake de banano.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=400"},

    # 8. Bebidas Calientes y Frías
    {"nombre": "Espresso", "precio": 10.0, "categoria": "Bebidas Calientes", "descripcion": "Espresso tradicional de 1 oz.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=400"},
    {"nombre": "Cortado", "precio": 13.0, "categoria": "Bebidas Calientes", "descripcion": "Cortado de 2 oz.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1534778101976-62847782c213?w=400"},
    {"nombre": "Dirty Coffee", "precio": 15.0, "categoria": "Bebidas Calientes", "descripcion": "Dirty coffee especial.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"},
    {"nombre": "Flat White", "precio": 25.0, "categoria": "Bebidas Calientes", "descripcion": "Flat white clásico.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"},
    {"nombre": "Cappuccino", "precio": 17.0, "categoria": "Bebidas Calientes", "descripcion": "Cappuccino clásico.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"},
    {"nombre": "Americano", "precio": 13.0, "categoria": "Bebidas Calientes", "descripcion": "Americano 8oz / 12oz.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"},
    {"nombre": "Café Negro", "precio": 10.0, "categoria": "Bebidas Calientes", "descripcion": "Café negro tradicional.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"},
    {"nombre": "Latte", "precio": 25.0, "categoria": "Bebidas Calientes", "descripcion": "Disponible en caliente o frío (12oz / 16oz).", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=400"},
    {"nombre": "Caramel Latte", "precio": 29.0, "categoria": "Bebidas Calientes", "descripcion": "Latte con toque de caramelo.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1585530927316-04cb5f1d8c89?w=400"},
    {"nombre": "Mocaccino", "precio": 29.0, "categoria": "Bebidas Calientes", "descripcion": "Café con chocolate y leche espumada.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1578314675249-a6919f3cbce3?w=400"},
    {"nombre": "Nikko Latte", "precio": 27.0, "categoria": "Bebidas Calientes", "descripcion": "Especialidad de la casa.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1570968915860-54d5c301fa9f?w=400"},
    {"nombre": "Cold Brew", "precio": 29.0, "categoria": "Bebidas Frías", "descripcion": "Café infusionado en frío.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1517701604599-bb29b565090c?w=400"},
    {"nombre": "Frappé Caramelo", "precio": 32.0, "categoria": "Bebidas Frías", "descripcion": "Bebida helada de café con caramelo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=400"},
    {"nombre": "Frappé Oreo", "precio": 32.0, "categoria": "Bebidas Frías", "descripcion": "Bebida helada con galleta Oreo.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?w=400"},
    {"nombre": "Matcha Latte", "precio": 28.0, "categoria": "Bebidas Calientes", "descripcion": "Té matcha en preparación caliente o fría.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?w=400"},
    {"nombre": "Matcha Berries", "precio": 30.0, "categoria": "Bebidas Frías", "descripcion": "Matcha con notas de frutos rojos.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?w=400"},
    {"nombre": "Chai Latte", "precio": 29.0, "categoria": "Bebidas Calientes", "descripcion": "Té chai especiado con leche.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=400"},
    {"nombre": "Chocolate con Leche", "precio": 26.0, "categoria": "Bebidas Calientes", "descripcion": "Chocolate caliente o frío con leche.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed?w=400"},
    {"nombre": "Chocolate con Agua", "precio": 22.0, "categoria": "Bebidas Calientes", "descripcion": "Chocolate tradicional preparado con agua.", "horario": "Ambos", "config_tamano": "elegir_ambos", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1542990253-0d0f5be5f0ed?w=400"},
    {"nombre": "Té", "precio": 16.0, "categoria": "Bebidas Calientes", "descripcion": "Selección de té caliente.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=400"},
    {"nombre": "Fizzy Soda", "precio": 22.0, "categoria": "Bebidas Frías", "descripcion": "Soda refrescante de la casa.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=400"},
    {"nombre": "Licuado con Leche", "precio": 26.0, "categoria": "Bebidas Frías", "descripcion": "Licuado natural con leche.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=400"},
    {"nombre": "Licuado con Agua", "precio": 22.0, "categoria": "Bebidas Frías", "descripcion": "Licuado natural con agua.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=400"},

    # 9. Métodos de Café Filtrado
    {"nombre": "Chemex", "precio": 20.0, "categoria": "Métodos", "descripcion": "Café filtrado en Chemex (frío o caliente).", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"},
    {"nombre": "V60", "precio": 20.0, "categoria": "Métodos", "descripcion": "Café filtrado por método V60.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"},
    {"nombre": "Prensa Francesa", "precio": 20.0, "categoria": "Métodos", "descripcion": "Café filtrado en prensa francesa.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=400"},

    # 10. Cócteles
    {"nombre": "Zacapa Cold Brew", "precio": 40.0, "categoria": "Cócteles y Café Filtrado", "descripcion": "Cóctel exclusivo con ron Zacapa y cold brew.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=400"},
    {"nombre": "Espresso Martini", "precio": 30.0, "categoria": "Cócteles y Café Filtrado", "descripcion": "Cóctel clásico con espresso.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1541658016709-82535e94bc69?w=400"},
    {"nombre": "Nikko Frost", "precio": 30.0, "categoria": "Cócteles y Café Filtrado", "descripcion": "Cóctel especial de la casa.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1514362545857-3bc16c4c7d1b?w=400"},
    {"nombre": "Carajillo", "precio": 35.0, "categoria": "Cócteles y Café Filtrado", "descripcion": "Carajillo tradicional con espresso y licor.", "horario": "Ambos", "config_tamano": "ninguno", "admite_promo": False, "imagen": "https://images.unsplash.com/photo-1541658016709-82535e94bc69?w=400"}
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
        res = requests.get(f"{SUPABASE_URL}/rest/v1/productos?select=nombre", headers=HEADERS)
        if res.status_code == 200:
            existentes = {p["nombre"] for p in res.json()}
            db_headers = {**HEADERS, "Content-Type": "application/json"}
            
            agregados = 0
            for prod in MENU_INICIAL_COMPLETO:
                if prod["nombre"] not in existentes:
                    requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=prod)
                    agregados += 1
            print(f"Sincronización completada. Se añadieron {agregados} productos nuevos.")
        else:
            print("Error al conectar con Supabase:", res.status_code, res.text)
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
        requests.post(f"{SUPABASE_URL}/rest/v1/productos", headers=db_headers, json=payload)
    except Exception as e: print("ERROR EN /admin/agregar:", e)
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
