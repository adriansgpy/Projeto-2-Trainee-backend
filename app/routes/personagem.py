from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from app.database import get_personagens_collection
from bson.json_util import dumps
import json
from app.routes.auth import get_current_user
from typing import List, Optional, Any

router_personagem = APIRouter(prefix="/personagens", tags=["personagens"])

client = MongoClient("mongodb://localhost:27017")
db = client["secretproject_db"]
characters_collection = db["personagens"]


class Capitulo(BaseModel):
    titulo: str
    completo: bool
    ultimoEvento: Optional[str]
    historicoLLM: List[Any] = []

class Character(BaseModel):
    nome: str
    image: str = ""
    hpAtual: int = 100
    bateriaHEV: int = 100
    inventario: List[str] = []
    ultimoCapitulo: Optional[str] = None
    capitulos: List[Capitulo] = []


CHAPTERS_TEMPLATE = [
    {"titulo": "Materiais Desconhecidos", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Consequências Inesperadas", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Complexo Administrativo", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Hostis à Vista", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Satélite", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Energia Ativada", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Nos Trilhos", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Detenção", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Processamento de Resíduos", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Ética Duvidosa", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Superfície em batalha", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Perdas suficiente", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Núcleo Lambda", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Xênon", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Covil de Gonarch", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Intruso", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "Nihilanth", "completo": False, "ultimoEvento": None, "historicoLLM": []},
    {"titulo": "O fim?", "completo": False, "ultimoEvento": None, "historicoLLM": []}
]

@router_personagem.post("/")
def create_character(character: Character, username: str = Depends(get_current_user)):
    character_dict = character.dict()
    character_dict.update({
        "owner_username": username,  
        "hpAtual": 100,
        "bateriaHEV": 100,
        "inventario": [],
        "ultimoCapitulo": None,
        "capitulos": [dict(c) for c in CHAPTERS_TEMPLATE] 
    })

    result = characters_collection.insert_one(character_dict)
    created = characters_collection.find_one({"_id": result.inserted_id})
    return json.loads(dumps(created))

@router_personagem.get("/")
def get_characters(username: str = Depends(get_current_user)):
    chars = list(characters_collection.find({"owner_username": username}))
    return json.loads(dumps(chars))

@router_personagem.delete("/{character_id}")
def delete_character(character_id: str, username: str = Depends(get_current_user)):
    result = characters_collection.delete_one({
        "_id": ObjectId(character_id),
        "owner_username": username
    })
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, 
            detail="Personagem não encontrado ou você não tem permissão"
        )
    return {"message": "Personagem deletado"}

@router_personagem.patch("/{character_id}")
def update_character(character_id: str, data: dict, username: str = Depends(get_current_user)):
    result = characters_collection.update_one(
        {"_id": ObjectId(character_id), "owner_username": username},
        {"$set": data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Personagem não encontrado ou você não tem permissão")
    updated = characters_collection.find_one({"_id": ObjectId(character_id)})
    return json.loads(dumps(updated))
