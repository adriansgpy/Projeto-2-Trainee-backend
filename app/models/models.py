from pydantic import BaseModel
from typing import List, Optional

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

class PlayerAction(BaseModel):
    action: str
    state: GameState
