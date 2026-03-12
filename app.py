from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai
import base64
import random
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Configuración Gemini (Sensei)
# -----------------------------

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-09-2025")

SENSEI_PROMPT = """Eres el Sensei del Billar, experto mundial en billar tres bandas, billar libre y snooker.

TU CONOCIMIENTO:
- Sistemas de diamantes: Ceulemans, Blomdahl, Plus, ESSE
- Maestros: Raymond Ceulemans, Dick Jaspers, Torbjorn Blomdahl, Frederic Caudron
- Fisica del billar, efectos, angulos, estrategias

REGLAS:
- Responde en maximo 5 oraciones
- Se tecnico pero claro
- Da un tip practico al final

Pregunta: """

ANALISIS_VIDEO_PROMPT = """Eres el Sensei del Billar, un experto mundial en billar tres bandas, billar libre y snooker.

Analiza este video/imagen de una jugada de billar y explica:

1. **Qué tipo de tiro es** (3 bandas, directo, de banda, etc.)
2. **La técnica utilizada** (efecto, velocidad, punto de ataque)
3. **Si fue bien ejecutado o no** y por qué
4. **Un consejo para mejorar**

IMPORTANTE - DETECCIÓN DE CHIRIPA:
Si la jugada parece ser una CHIRIPA (suerte, casualidad, no intencional), debes:
- Detectarla con humor
- Usar frases cómicas como:
  * "¡Eso fue más suerte que técnica, pero igual cuenta!"
  * "El billar tiene un dicho: 'La suerte también se entrena'... pero eso fue pura chiripa, mi amigo"
  * "Ni tú sabías que iba a entrar, ¿verdad? ¡Chiripa de oro!"
  * "Esa bola tenía GPS divino, porque técnica no fue"
  * "¡Hasta la bola se sorprendió de entrar!"
  * "Eso no está en ningún libro de Ceulemans... ¡pero funcionó!"
- Pero siempre termina con un consejo real para que aprenda

Señales de chiripa:
- Trayectorias erráticas o inesperadas
- Rebotes múltiples sin sentido aparente
- Bola que entra de casualidad
- Expresión de sorpresa del jugador

Responde de forma amigable, técnica pero con humor cuando sea apropiado.
"""


class ChatRequest(BaseModel):
    mensaje: str


# -----------------------------
# Config Supabase para overlay
# -----------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")


async def fetch_overlay_state_from_supabase(match_id: str):
    """
    Consulta la vista overlay_state en Supabase y devuelve
    el estado del marcador para un match_id concreto.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=500,
            detail="Supabase no está configurado correctamente (revisa SUPABASE_URL y SUPABASE_SERVICE_KEY).",
        )

    url = f"{SUPABASE_URL}/rest/v1/overlay_state"

    # IMPORTANTE: la vista overlay_state expone la columna match_id.
    # Filtramos por match_id para que coincida con el parámetro recibido.
    params = {"match_id": f"eq.{match_id}", "limit": "1"}

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error conectando con Supabase: {exc}",
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Error desde Supabase ({response.status_code}): {response.text}",
        )

    try:
        data = response.json()
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="Respuesta inválida de Supabase (no es JSON).",
        )

    if not data:
        # No se encontró partida para ese match_id
        raise HTTPException(
            status_code=404,
            detail="No se encontró estado de overlay para ese match_id.",
        )

    # La vista overlay_state ya debe devolver las columnas correctas.
    # Devolvemos directamente la primera fila.
    row = data[0]
    return row


# -----------------------------
# Endpoints API
# -----------------------------


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Sensei del Billar API v2",
        "features": ["chat", "video_analysis", "overlay"],
    }


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        response = model.generate_content(SENSEI_PROMPT + request.mensaje)
        return {"respuesta": response.text}
    except Exception:
        return {
            "respuesta": "Error procesando tu pregunta. Intenta de nuevo.",
            "error": True,
        }


@app.post("/analizar-video")
async def analizar_video(
    video: UploadFile = File(...), tipo: str = Form(default="jugada")
):
    try:
        contenido = await video.read()
        video_base64 = base64.b64encode(contenido).decode("utf-8")
        content_type = video.content_type or "video/mp4"

        if tipo == "chiripa":
            prompt = (
                ANALISIS_VIDEO_PROMPT
                + "\n\nNOTA: El usuario cree que esto puede ser una CHIRIPA. Analiza con humor si realmente lo es."
            )
        else:
            prompt = ANALISIS_VIDEO_PROMPT

        response = model.generate_content(
            [
                {
                    "mime_type": content_type,
                    "data": video_base64,
                },
                prompt,
            ]
        )

        return {
            "respuesta": response.text,
            "tipo_analisis": tipo,
            "exito": True,
        }

    except Exception as e:
        respuestas_fallback = [
            "¡Ups! Mi visión de Sensei está nublada hoy. El video no se pudo procesar. ¿Puedes intentar con uno más corto o en otro formato?",
            "Hmm, parece que este video tiene más misterio que una chiripa de campeonato. Intenta subirlo de nuevo.",
            "El video se resistió a mi análisis como una bola con mucho efecto. ¿Probamos de nuevo?",
        ]
        return {
            "respuesta": random.choice(respuestas_fallback),
            "error": str(e),
            "exito": False,
        }


@app.post("/analizar-imagen")
async def analizar_imagen(
    imagen: UploadFile = File(...), tipo: str = Form(default="jugada")
):
    try:
        contenido = await imagen.read()
        imagen_base64 = base64.b64encode(contenido).decode("utf-8")
        content_type = imagen.content_type or "image/jpeg"

        if tipo == "chiripa":
            prompt = (
                ANALISIS_VIDEO_PROMPT
                + "\n\nNOTA: El usuario cree que esto puede ser una CHIRIPA. Analiza con humor si realmente lo es."
            )
        else:
            prompt = ANALISIS_VIDEO_PROMPT

        response = model.generate_content(
            [
                {
                    "mime_type": content_type,
                    "data": imagen_base64,
                },
                prompt,
            ]
        )

        return {
            "respuesta": response.text,
            "tipo_analisis": tipo,
            "exito": True,
        }

    except Exception as e:
        return {
            "respuesta": "No pude analizar la imagen. ¿Puedes intentar con otra?",
            "error": str(e),
            "exito": False,
        }


@app.get("/overlay/state")
async def overlay_state(
    match_id: str = Query(..., description="UUID de la partida (partidas.id)"),
):
    """
    Endpoint para el overlay de marcadores (OBS / Streamlabs).
    Ejemplo de uso:
    GET /overlay/state?match_id=UUID
    """
    return await fetch_overlay_state_from_supabase(match_id)
