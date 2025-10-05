"""
API utilizada no front-end Angular contendo todas as rotas, classes modelos e funções auxiliares para o RPG textual funcionar
"""

#imports
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import requests
import json

#Configurações do LLM
GOOGLE_API_KEY = "AIzaSyCSB2VvJkwkCcHbXL5m1ganWJ3xn15Pui8"
MODEL = "gemini-2.0-flash"  
BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GOOGLE_API_KEY}"

#Classes modelos
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

#Router do LLM
llm_router = APIRouter(prefix="/llm", tags=["LLM"])


#Invocar o gemini com prompt e output tokens
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
        return '{"narrative": "O encontro começa...", "choices": ["Atacar", "Defender", "Usar Item"]}'

#Converter o output do LLM em JSON válido
def safe_json_parse(text: str) -> dict:
    """Converte string JSON para dict, transforma narrativa em lista e normaliza turn_result"""
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


#Checar se o jogo já acabou
def check_game_over(player: dict, enemy: dict) -> Optional[dict]:
    """Retorna um dict com resultado se algum HP for zero, ou None se o jogo continuar."""
    if player["hp"] <= 0:
        return {"game_over": True, "winner": "enemy", "loser": "player"}
    elif enemy["hp"] <= 0:
        return {"game_over": True, "winner": "player", "loser": "enemy"}
    return None


#Gerar turno com base no desenvolvimento do jogo (gerado a partir das ações do jogador)
def generate_dynamic_turn(player_action: str, game_state: dict) -> dict:
    prompt = f"""
    Você é um mestre de RPG.
    O jogador digitou: "{player_action}".
    Estado atual do jogo: {json.dumps(game_state, ensure_ascii=False)}

    Regras:
    - Respeite a stamina de cada personagem em cada turno
    - Não coloque o HP e stamina dos personagens na narrativa
    - Não gere textos gigantes
    - Narre a luta de forma zoeira e cômica.
    - Mostre ações do jogador e da lenda.
    - Atualize HP e stamina de ambos se necessário.
    - Sugira 3 próximas ações.
    - Forneça um resumo das mudanças de HP/Stamina separadamente no campo 'turn_result', no formato:
    {{
    "player": {{"hp_change": -10, "stamina_change": -5}},
    "enemy": {{"hp_change": -5, "stamina_change": -10}}
    }}
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


#Gerar narrativa inicial utilizando o contexto das lendas 
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

    if not data["status"]:
        data["status"] = {"player": game_state["player"], "enemy": game_state["enemy"]}
    return data


#Rota: Iniciar o jogo
@llm_router.post("/start_game")
def start_game(request: StartGameRequest):
    game_state = request.state.dict()
    response = generate_initial_narrative(game_state)
    return response

#Rota: Processar o turno 
@llm_router.post("/turn")
def process_turn(action: PlayerAction):
    game_state = action.state.dict()
    response = generate_dynamic_turn(action.action, game_state)
    
    game_over = check_game_over(response["status"]["player"], response["status"]["enemy"])
    if game_over:
        response["game_over"] = game_over

    return response
