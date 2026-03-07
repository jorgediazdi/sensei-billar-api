from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import google.generativeai as genai

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

SENSEI_PROMPT = """Eres el Sensei del Billar, experto mundial en billar tres bandas.

TU CONOCIMIENTO:
- Sistemas de diamantes: Ceulemans, Blomdahl, Plus, ESSE
- Maestros: Raymond Ceulemans, Dick Jaspers, Torbjorn Blomdahl, Frederic Caudron
- Fisica del billar, efectos, angulos, estrategias

REGLAS:
- Responde en maximo 5 oraciones
- Se tecnico pero claro
- Da un tip practico al final

Pregunta: """

class ChatRequest(BaseModel):
    mensaje: str

@app.get("/")
def root():
    return {"status": "online", "service": "Sensei del Billar"}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        response = model.generate_content(SENSEI_PROMPT + request.mensaje)
        return {"respuesta": response.text}
    except Exception as e:
        return {"respuesta": "Error. Intenta de nuevo.", "error": True}
