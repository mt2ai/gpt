import os
import sys
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

# Añadir el directorio raíz al path para importar core
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from core.engine import Metin2Engine

app = FastAPI(title="Metin2 Oracle", description="Asistente de consulta determinista para Metin2")

# Inicializar motor
print("[Server] Cargando motor de Metin2 y catálogo de 3.421 entidades...")
engine = Metin2Engine()
print("[Server] Motor listo.")

# Rutas estáticas para la web
WEB_DIR = os.path.join(CURRENT_DIR, "web")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def get_index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))

@app.get("/style.css")
def get_css():
    return FileResponse(os.path.join(WEB_DIR, "style.css"), media_type="text/css")

@app.get("/app.js")
def get_js():
    return FileResponse(os.path.join(WEB_DIR, "app.js"), media_type="application/javascript")

@app.get("/api/ask")
def ask(
    q: str = Query(..., description="Consulta en lenguaje natural"),
    session_id: str = Query("default", description="ID de sesión para memoria conversacional")
):
    if not q or not q.strip():
        return JSONResponse({"success": False, "message": "Por favor escribe una consulta."})
        
    result = engine.resolve_query(q, session_id=session_id)
    return JSONResponse(result)

if __name__ == "__main__":
    # Escucha en 0.0.0.0 para que puedas conectarte desde tu celular en la misma red Wi-Fi
    print("Iniciando servidor en http://0.0.0.0:8000...")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
