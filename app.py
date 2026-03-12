from fastapi import FastAPI, File, UploadFile, Form, HTTPException
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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

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
- Rebotes múltiples sin sentid
