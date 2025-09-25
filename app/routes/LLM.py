from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

GEMINI_API_KEY = "SUA_CHAVE_API_AQUI"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/messages:generate"

class Jogador(BaseModel):
    hp: int
    maxHp: int
    hevBattery: int
    inventory: list

class Payload(BaseModel):
    contexto: str
    armas: list
    inimigos: list
    estadoJogador: Jogador
    acaoJogador: str = None

@app.post("/api/narrativa")
def gerar_narrativa(payload: Payload):
    prompt = f"""
    Você é um narrador de RPG baseado em Black Mesa. O jogador está neste contexto:
    {payload.contexto}

    Armas disponíveis: {', '.join(payload.armas)}
    Inimigos presentes: {', '.join(payload.inimigos)}
    Estado do jogador: {payload.estadoJogador.dict()}

    O jogador escolheu: {payload.acaoJogador or 'Nenhuma ação ainda'}

    - Escreva uma narrativa envolvente.
    - Sugira até 3 escolhas possíveis.
    - Atualize o estado do jogador (HP, inventário, bateria).
    - Termine a narrativa com clareza de fim de trecho do capítulo se aplicável.
    """

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gemini-3",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(GEMINI_API_URL, json=data, headers=headers)
    result = response.json()

    narrativa = result['choices'][0]['message']['content']

    # Aqui você pode gerar sugestões de escolhas e atualizar o estado do jogador
    return {
        "narrativa": narrativa,
        "escolhas": ["Explorar laboratório", "Seguir corredor", "Checar equipamento"],
        "atualizacoes": payload.estadoJogador.dict()
    }
