from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai
import base64
import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
def root():
    return {"status": "online", "service": "Sensei del Billar API v2", "features": ["chat", "video_analysis"]}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        response = model.generate_content(SENSEI_PROMPT + request.mensaje)
        return {"respuesta": response.text}
    except Exception as e:
        return {"respuesta": "Error procesando tu pregunta. Intenta de nuevo.", "error": True}

@app.post("/analizar-video")
async def analizar_video(video: UploadFile = File(...), tipo: str = Form(default="jugada")):
    try:
        # Leer el archivo
        contenido = await video.read()
        
        # Convertir a base64
        video_base64 = base64.b64encode(contenido).decode('utf-8')
        
        # Determinar el tipo MIME
        content_type = video.content_type or "video/mp4"
        
        # Crear el prompt según el tipo
        if tipo == "chiripa":
            prompt = ANALISIS_VIDEO_PROMPT + "\n\nNOTA: El usuario cree que esto puede ser una CHIRIPA. Analiza con humor si realmente lo es."
        else:
            prompt = ANALISIS_VIDEO_PROMPT
        
        # Usar Gemini Vision para analizar
        # Para videos, Gemini necesita el archivo en formato específico
        response = model.generate_content([
            {
                "mime_type": content_type,
                "data": video_base64
            },
            prompt
        ])
        
        return {
            "respuesta": response.text,
            "tipo_analisis": tipo,
            "exito": True
        }
        
    except Exception as e:
        # Respuesta de fallback con humor
        respuestas_fallback = [
            "¡Ups! Mi visión de Sensei está nublada hoy. El video no se pudo procesar. ¿Puedes intentar con uno más corto o en otro formato?",
            "Hmm, parece que este video tiene más misterio que una chiripa de campeonato. Intenta subirlo de nuevo.",
            "El video se resistió a mi análisis como una bola con mucho efecto. ¿Probamos de nuevo?"
        ]
        return {
            "respuesta": random.choice(respuestas_fallback),
            "error": str(e),
            "exito": False
        }

@app.post("/analizar-imagen")
async def analizar_imagen(imagen: UploadFile = File(...), tipo: str = Form(default="jugada")):
    try:
        contenido = await imagen.read()
        imagen_base64 = base64.b64encode(contenido).decode('utf-8')
        content_type = imagen.content_type or "image/jpeg"
        
        if tipo == "chiripa":
            prompt = ANALISIS_VIDEO_PROMPT + "\n\nNOTA: El usuario cree que esto puede ser una CHIRIPA. Analiza con humor si realmente lo es."
        else:
            prompt = ANALISIS_VIDEO_PROMPT
        
        response = model.generate_content([
            {
                "mime_type": content_type,
                "data": imagen_base64
            },
            prompt
        ])
        
        return {
            "respuesta": response.text,
            "tipo_analisis": tipo,
            "exito": True
        }
        
    except Exception as e:
        return {
            "respuesta": "No pude analizar la imagen. ¿Puedes intentar con otra?",
            "error": str(e),
            "exito": False
        }
