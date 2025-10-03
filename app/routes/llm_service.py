from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import requests
import json

# =====================================
# CONFIG
# =====================================
GOOGLE_API_KEY = "AIzaSyCSB2VvJkwkCcHbXL5m1ganWJ3xn15Pui8"

PRIMARY_MODEL = "gemini-2.5-flash-lite"   # Modelo principal
SECONDARY_MODEL = "gemini-2.0-flash-lite" # Fallback
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# =====================================
# MODELOS Pydantic
# =====================================
class PlayerState(BaseModel):
    nome: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int

class EnemyState(BaseModel):
    nome: str
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    descricao: str       # NOVO: descrição da lenda
    ataqueEspecial: str  # NOVO: ataque especial

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

llm_router = APIRouter(prefix="/llm", tags=["LLM"])

# =====================================
# FUNÇÕES DE CHAMADA LLM
# =====================================
def call_gemini_model(prompt: str, model: str, max_output_tokens: int = 1000) -> str:
    """Chama um modelo específico do Gemini"""
    url = f"{BASE_URL}/{model}:generateContent?key={GOOGLE_API_KEY}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": max_output_tokens}
    }
    response = requests.post(url, headers={"Content-Type": "application/json"}, json=data, timeout=15)
    response.raise_for_status()
    resp_json = response.json()
    return resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()


def call_gemini_with_fallback(prompt: str, max_output_tokens: int = 1000) -> str:
    """Tenta modelo primário -> secundário -> JSON fixo"""
    try:
        return call_gemini_model(prompt, PRIMARY_MODEL, max_output_tokens)
    except Exception as e1:
        print("Erro no modelo primário:", e1)

    try:
        return call_gemini_model(prompt, SECONDARY_MODEL, max_output_tokens)
    except Exception as e2:
        print("Erro no modelo secundário:", e2)

    print("Todos os modelos falharam, usando narrativa padrão")
    return '{"narrativa": ["O encontro começa..."], "escolhas": ["Atacar", "Defender", "Usar Item"], "status": {}, "turn_result": {}}'

# =====================================
# UTILITÁRIOS
# =====================================
def safe_json_parse(text: str) -> dict:
    """Converte string JSON para dict seguro"""
    try:
        data = json.loads(text)
    except:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])
        except:
            data = {"narrativa": [text], "escolhas": ["Atacar", "Defender", "Usar Item"], "status": {}, "turn_result": {}}

    narrativa = []
    if "narrativa" in data and isinstance(data["narrativa"], list):
        narrativa = data["narrativa"]
    elif "narrativa" in data and isinstance(data["narrativa"], str):
        narrativa = [line.strip() for line in data["narrativa"].split("\n") if line.strip()]

    escolhas = data.get("escolhas") or data.get("choices") or ["Atacar", "Defender", "Usar Item"]
    status = data.get("status") or {}
    default_turn_result = {
        "player": {"hp_change": 0, "stamina_change": 0},
        "enemy": {"hp_change": 0, "stamina_change": 0}
    }
    turn_result = {**default_turn_result, **data.get("turn_result", {})}

    return {
        "narrativa": narrativa,
        "escolhas": escolhas,
        "status": status,
        "turn_result": turn_result
    }

def check_game_over(player: dict, enemy: dict) -> Optional[dict]:
    """Verifica se o jogo terminou"""
    if player["hp"] <= 0:
        return {"game_over": True, "winner": "enemy", "loser": "player"}
    elif enemy["hp"] <= 0:
        return {"game_over": True, "winner": "player", "loser": "enemy"}
    return None

# =====================================
# FUNÇÕES DE GERAÇÃO
# =====================================
def generate_dynamic_turn(player_action: str, game_state: dict) -> dict:
    # Inclui descrição e ataque especial da lenda no prompt
    prompt = f"""
Você é um mestre de RPG.
O jogador digitou: "{player_action}".
Capítulo: {game_state['chapter']}
O jogador: {json.dumps(game_state['player'], ensure_ascii=False)}
A lenda: {json.dumps(game_state['enemy'], ensure_ascii=False)}

História da lenda: {game_state['enemy'].get('descricao')}
Ataque especial: {game_state['enemy'].get('ataqueEspecial')}

Regras:
- Respeite a stamina de cada personagem em cada turno
- Use a história, descrição e ataque especial da lenda
- Não coloque HP e stamina na narrativa
- Narre a luta de forma zoeira e cômica
- Sugira 3 próximas ações
- Forneça resumo das mudanças de HP/Stamina separadamente no campo 'turn_result'
- Responda apenas em JSON válido no formato:
{{
  "narrativa": ["..."],
  "escolhas": ["...", "...", "..."],
  "status": {{
    "player": {{...}},
    "enemy": {{...}}
  }},
  "turn_result": {{}}
}}
"""
    text = call_gemini_with_fallback(prompt, max_output_tokens=1000)
    data = safe_json_parse(text)

    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}

    data["player"] = data["status"]["player"]
    data["enemy"] = data["status"]["enemy"]

    game_over = check_game_over(data["status"]["player"], data["status"]["enemy"])
    if game_over:
        data["game_over"] = game_over

    return data

def generate_initial_narrative(game_state: dict) -> dict:
    # Inclui descrição e ataque especial da lenda no prompt
    prompt = f"""
Você é um mestre de RPG maluco e engraçado.
Inicie o capítulo: {game_state['chapter']}
O jogador: {json.dumps(game_state['player'], ensure_ascii=False)}
A lenda: {json.dumps(game_state['enemy'], ensure_ascii=False)}

História da lenda: {game_state['enemy'].get('descricao')}
Ataque especial: {game_state['enemy'].get('ataqueEspecial')}

Regras:
- Narre a entrada da lenda e do jogador de forma zoeira
- Use a descrição e ataque especial da lenda
- Sugira 3 ações iniciais
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
    text = call_gemini_with_fallback(prompt, max_output_tokens=800)
    data = safe_json_parse(text)

    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}
    return data

# =====================================
# ENDPOINTS
# =====================================
@llm_router.post("/start_game")
def start_game(request: StartGameRequest):
    game_state = request.state.dict()
    response = generate_initial_narrative(game_state)
    return response

@llm_router.post("/turn")
def process_turn(action: PlayerAction):
    game_state = action.state.dict()
    response = generate_dynamic_turn(action.action, game_state)

    game_over = check_game_over(response["status"]["player"], response["status"]["enemy"])
    if game_over:
        response["game_over"] = game_over

    return response
