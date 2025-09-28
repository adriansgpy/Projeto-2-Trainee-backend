from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import requests
import json

GOOGLE_API_KEY = "AIzaSyCSB2VvJkwkCcHbXL5m1ganWJ3xn15Pui8"
MODEL = "gemini-2.0-flash"
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GOOGLE_API_KEY}"

# -------------------- MODELS --------------------

class PlayerState(BaseModel):
    nome: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    inventario: List[str]

class EnemyState(BaseModel):
    nome: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int

class GameState(BaseModel):
    player: PlayerState
    enemy: EnemyState
    chapter: str
    narrative: str
    choices: Optional[List[str]] = []

class StartGameRequest(BaseModel):
    state: GameState

class PlayerAction(BaseModel):
    action: str
    state: GameState

# -------------------- ROUTER --------------------

llm_router = APIRouter(prefix="/llm", tags=["LLM"])

# -------------------- FUNÇÕES --------------------

def call_gemini(prompt: str, max_output_tokens: int = 1000) -> str:
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": max_output_tokens}
    }
    try:
        response = requests.post(BASE_URL, headers={"Content-Type": "application/json"}, json=data, timeout=15)
        response.raise_for_status()
        resp_json = response.json()
        text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        print("Erro na chamada ao Gemini:", e)
        # fallback em português
        return '{"narrativa": ["O encontro começa..."], "escolhas": ["Atacar", "Defender", "Usar Item"], "status": {}}'

def safe_json_parse(text: str) -> dict:
    """Converte string JSON para dict e transforma narrativa em lista"""
    try:
        data = json.loads(text)
    except:
        # tenta extrair JSON de dentro de texto
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])
        except:
            data = {"narrativa": [text], "escolhas": ["Atacar", "Defender", "Usar Item"], "status": {}}

    # normaliza narrativa
    narrativa = []
    if "narrativa" in data and isinstance(data["narrativa"], list):
        narrativa = data["narrativa"]
    elif "narrativa" in data and isinstance(data["narrativa"], str):
        narrativa = [line.strip() for line in data["narrativa"].split("\n") if line.strip()]
    elif "narrative" in data and isinstance(data["narrative"], str):
        narrativa = [line.strip() for line in data["narrative"].split("\n") if line.strip()]

    # normaliza escolhas
    escolhas = data.get("escolhas") or data.get("choices") or ["Atacar", "Defender", "Usar Item"]

    status = data.get("status") or {}

    return {
        "narrativa": narrativa,
        "escolhas": escolhas,
        "status": status
    }

def generate_initial_narrative(game_state: dict) -> dict:
    prompt = f"""
Você é um mestre de RPG maluco e engraçado.
Inicie o capítulo: {game_state['chapter']}.
O jogador: {json.dumps(game_state['player'], ensure_ascii=False)}
A lenda: {json.dumps(game_state['enemy'], ensure_ascii=False)}

Regras:
- Narre a entrada da lenda e do jogador de forma zoeira.
- Sugira 3 ações iniciais.
- Responda apenas em JSON válido no formato:
{{
  "narrativa": ["..."],
  "escolhas": ["...", "...", "..."],
  "status": {{
      "player": {{...}},
      "enemy": {{...}}
  }}
}}
"""
    text = call_gemini(prompt, max_output_tokens=800)
    data = safe_json_parse(text)

    # fallback para status
    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}

    # desmembra status para frontend
    data["player"] = data["status"]["player"]
    data["enemy"] = data["status"]["enemy"]

    return data

def generate_dynamic_turn(player_action: str, game_state: dict) -> dict:
    prompt = f"""
Você é um mestre de RPG.
O jogador digitou: "{player_action}".
Estado atual do jogo: {json.dumps(game_state, ensure_ascii=False)}

Regras:
- Narre a luta de forma zoeira e cômica.
- Mostre ações do jogador e da lenda.
- Atualize HP e stamina de ambos se necessário.
- Sugira 3 próximas ações.
- Responda apenas em JSON válido no formato:
{{
  "narrativa": ["..."],
  "escolhas": ["...", "...", "..."],
  "status": {{
      "player": {{...}},
      "enemy": {{...}}
  }}
}}
"""
    text = call_gemini(prompt, max_output_tokens=1000)
    data = safe_json_parse(text)

    # fallback para status
    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}

    # desmembra status para frontend
    data["player"] = data["status"]["player"]
    data["enemy"] = data["status"]["enemy"]

    return data

# -------------------- ROTAS --------------------

@llm_router.post("/start_game")
def start_game(request: StartGameRequest):
    game_state = request.state.dict()
    response = generate_initial_narrative(game_state)
    return response

@llm_router.post("/turn")
def process_turn(action: PlayerAction):
    game_state = action.state.dict()
    response = generate_dynamic_turn(action.action, game_state)
    return response
