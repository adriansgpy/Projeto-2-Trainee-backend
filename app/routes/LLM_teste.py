from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import requests
import os
import json

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAeTk6f8l0aXqX7KwLr0hxh9synVfIo7w8")
GEMINI_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class ChapterStartRequest(BaseModel):
    chapter: int
    context: str
    player_state: dict

class TurnRequest(BaseModel):
    last_narrative: str
    action: str
    player_state: dict

def call_gemini(prompt: str):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}

    response = requests.post(GEMINI_MODEL_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao extrair resposta do LLM")

def parse_llm_json(text: str):
    """
    Remove blocos de markdown ```json ... ``` e retorna JSON válido
    """
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned)

@router.post("/start_chapter")
def start_chapter(req: ChapterStartRequest):
    prompt = f"""
Você é o narrador do jogo Black Mesa. Narre as cenas com detalhes respeitando a história do jogo half life, não faça textos gigantes, narre de forma cativante

Regras:
- Narre APENAS o início do capítulo atual.
- Nunca avance para outro capítulo sem ser instruído.
- Respeite a história original de Half-Life.
- SEMPRE responda em JSON.

Formato esperado:
{{
  "narrativa": "descrição inicial",
  "choices": ["opção1", "opção2", "opção3"]
}}

Capítulo: {req.chapter}
Contexto: {req.context}
Estado inicial do jogador: {req.player_state}
"""

    generated_text = call_gemini(prompt)

    try:
        parsed = parse_llm_json(generated_text)
    except Exception:
        raise HTTPException(status_code=500, detail=f"LLM não retornou JSON válido: {generated_text}")

    return parsed


@router.post("/turn")
def turn(req: TurnRequest):
    prompt = f"""
Você é o narrador do jogo Black Mesa. Narre as cenas com detalhes respeitando a história do jogo half life, não faça textos gigantes, narre de forma cativante

Regras:
- Narre o que acontece APENAS após a ação escolhida.
- Nunca avance de capítulo sem instrução.
- Respeite a história original de Half-Life.
- SEMPRE responda em JSON.

Formato esperado:
{{
  "narrativa": "descrição do que acontece",
  "efeitos": {{
    "hp": -10,
    "hevBattery": 0,
    "inventarioAdd": ["itemX"],
    "inventarioRemove": []
  }},
  "choices": ["opção1", "opção2"]
}}

Última narrativa: {req.last_narrative}
Ação do jogador: {req.action}
Estado do jogador: {req.player_state}
"""

    generated_text = call_gemini(prompt)

    try:
        parsed = parse_llm_json(generated_text)
    except Exception:
        raise HTTPException(status_code=500, detail=f"LLM não retornou JSON válido: {generated_text}")

    return parsed