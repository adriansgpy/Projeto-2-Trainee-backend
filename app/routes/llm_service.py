from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import requests
import json

GOOGLE_API_KEY = "AIzaSyCSB2VvJkwkCcHbXL5m1ganWJ3xn15Pui8"

MODEL = "gemini-2.0-flash"  
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GOOGLE_API_KEY}"

# ---------------- MODELOS ----------------
class PlayerState(BaseModel):
    nome: str
    classe: Optional[str] = "Guerreiro"  # <- classe do jogador
    hp: int
    max_hp: int
    stamina: int
    max_stamina: int
    inventario: List[str]

class EnemyState(BaseModel):
    nome: str
    descricao: Optional[str] = ""
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

# ---------------- ROUTER ----------------
llm_router = APIRouter(prefix="/llm", tags=["LLM"])

# ---------------- FUNÇÕES AUXILIARES ----------------
def call_gemini(prompt: str, max_output_tokens: int = 1000) -> str:
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": max_output_tokens}
    }
    try:
        response = requests.post(BASE_URL, headers={"Content-Type": "application/json"}, json=data, timeout=15)
        response.raise_for_status()
        resp_json = response.json()
        text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
        return text.strip()
    except Exception as e:
        print("Erro na chamada ao Gemini:", e)
        return '{"narrativa": "O encontro começa...", "choices": ["Atacar", "Defender", "Usar Item"]}'

def safe_json_parse(text: str) -> dict:
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

    turn_result = data.get("turn_result") or {
        "player": {"hp_change": 0, "stamina_change": 0},
        "enemy": {"hp_change": 0, "stamina_change": 0}
    }

    return {
        "narrativa": narrativa,
        "escolhas": escolhas,
        "status": status,
        "turn_result": turn_result
    }

def check_game_over(player: dict, enemy: dict) -> Optional[dict]:
    if player["hp"] <= 0:
        return {"game_over": True, "winner": "enemy", "loser": "player"}
    elif enemy["hp"] <= 0:
        return {"game_over": True, "winner": "player", "loser": "enemy"}
    return None

# ---------------- LÓGICA DO TURNO ----------------
def generate_dynamic_turn(player_action: str, game_state: dict) -> dict:
    enemy_desc = game_state['enemy'].get('descricao', '')
    player_class = game_state['player'].get('classe', 'Guerreiro')

    prompt = f"""
    Você é um mestre de RPG.
    O jogador ({player_class}) digitou: "{player_action}".
    Estado atual do jogo: {json.dumps(game_state, ensure_ascii=False)}
    Contexto da lenda ({game_state['enemy']['nome']}): {enemy_desc}

    Regras:
    - Use a descrição da lenda e a classe do jogador para criar o contexto da luta.
    - Não coloque o HP e stamina dos personagens na narrativa
    - Não gere textos gigantes
    - Narre a luta de forma zoeira e cômica.
    - Mostre ações do jogador e da lenda.
    - Atualize HP de ambos se necessário.
    - Sugira 3 próximas ações.
    - Forneça um resumo das mudanças de HP separadamente no campo 'turn_result', no formato:
    {{
        "player": {{"hp_change": -10, "stamina_change": -5}},
        "enemy": {{"hp_change": -5, "stamina_change": -10}}
    }}
    - Responda apenas em JSON válido no formato:
    {{
        "narrativa": ["..."],
        "escolhas": ["...", "...", "..."],
        "status": {{"player": {{...}}, "enemy": {{...}}}},
        "turn_result": {{}}
    }}
    """
    text = call_gemini(prompt, max_output_tokens=1000)
    data = safe_json_parse(text)

    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}

    data["player"] = data["status"]["player"]
    data["enemy"] = data["status"]["enemy"]

    game_over = check_game_over(data["status"]["player"], data["status"]["enemy"])
    if game_over:
        data["game_over"] = game_over

    return data

# ---------------- LÓGICA INICIAL ----------------
def generate_initial_narrative(game_state: dict) -> dict:
    enemy_desc = game_state['enemy'].get('descricao', '')
    player_class = game_state['player'].get('classe', 'Guerreiro')

    prompt = f"""
        Você é um mestre de RPG maluco e engraçado.
        Inicie o capítulo: {game_state['chapter']}.
        O jogador ({player_class}): {json.dumps(game_state['player'], ensure_ascii=False)}
        A lenda ({game_state['enemy']['nome']}): {enemy_desc}

        Regras:
        - Use a classe do jogador e a descrição da lenda para criar o contexto da batalha.
        - Não coloque o HP e stamina dos personagens na narrativa
        - Narre a entrada da lenda e do jogador de forma zoeira e engraçada.
        - Sugira 3 ações iniciais.
        - Responda apenas em JSON válido no formato:
        {{
            "narrativa": ["..."],
            "escolhas": ["...", "...", "..."],
            "status": {{"player": {{...}}, "enemy": {{...}}}}
        }}
    """
    text = call_gemini(prompt, max_output_tokens=800)
    data = safe_json_parse(text)

    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}
    return data

# ---------------- ENDPOINTS ----------------
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
