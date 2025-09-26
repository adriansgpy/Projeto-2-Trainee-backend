from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
import requests
import os
import json
import re

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAeTk6f8l0aXqX7KwLr0hxh9synVfIo7w8")
GEMINI_MODEL_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class ChapterStartRequest(BaseModel):
    chapter: int
    context: str
    player_state: dict
    rules: list[str] = []


class TurnRequest(BaseModel):
    last_narrative: str
    action: str
    player_state: dict
    rules: list[str] = []

def call_gemini(prompt: str):
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}

    response = requests.post(GEMINI_MODEL_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair resposta do LLM: {e}")


def parse_llm_json(text: str):
    """
    Extrai o primeiro JSON válido da resposta do LLM.
    Remove possíveis blocos ```json ... ``` extras.
    """
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise ValueError(f"Nenhum JSON encontrado: {text}")

    return json.loads(match.group(0))


def validate_response(parsed: dict, required_fields: list[str]):
    """
    Garante que os campos obrigatórios estão presentes.
    """
    for field in required_fields:
        if field not in parsed:
            raise HTTPException(
                status_code=500,
                detail=f"Campo obrigatório '{field}' ausente na resposta do LLM: {parsed}"
            )
    return parsed


@router.post("/start_chapter")
def start_chapter(req: ChapterStartRequest):
    rules_text = "\n".join([f"- {r}" for r in req.rules]) if req.rules else "Nenhuma regra extra."

    prompt = f"""
Você é o narrador do jogo Black Mesa. Narre as cenas com detalhes respeitando a história do jogo Half-Life. 
Não faça textos gigantes, narre de forma cativante.

Regras globais:
- Narre APENAS o início do capítulo atual.
- Nunca avance para outro capítulo sem ser instruído.
- Respeite a história original de Half-Life.
- SEMPRE responda em JSON.

Regras específicas deste capítulo:
{rules_text}

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
        validate_response(parsed, ["narrativa", "choices"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM não retornou JSON válido: {generated_text} | Erro: {e}")

    return parsed


@router.post("/turn")
def turn(req: TurnRequest):
    rules_text = "\n".join([f"- {r}" for r in req.rules]) if req.rules else "Nenhuma regra extra."

    prompt = f"""
Você é o narrador do jogo Black Mesa. Narre as cenas com detalhes respeitando a história do jogo Half-Life. 
Não faça textos gigantes, narre de forma cativante.

Regras globais:
- Narre o que acontece APENAS após a ação escolhida.
- Nunca avance de capítulo sem instrução.
- Respeite a história original de Half-Life.
- Sempre indique claramente se o jogador levou dano, e quantos pontos perdeu.
- SEMPRE responda em JSON.

Regras específicas deste capítulo:
{rules_text}

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
        validate_response(parsed, ["narrativa", "efeitos", "choices"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM não retornou JSON válido: {generated_text} | Erro: {e}")

    return parsed
