
"""
API utilizada para criar personagens, listar e deletar
"""

#imports
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional
import json
from pydantic import BaseModel

#import da collection dos personagens
from app.database import get_personagens_collection 
from app.routes.auth import get_current_user 
from bson.json_util import dumps 

#Coleção de personagens ao inicializar o router
router_personagem = APIRouter(prefix="/personagens", tags=["personagens"])
characters_collection = get_personagens_collection()

# Modelagem de dados (Pydantic)
class Character(BaseModel):
    nome: str
    role: str
    hpAtual: int
    stamina: int
    ataqueEspecial: str
    inventario: List[str] = []
    image: Optional[str] = ""

#Rota: Criar Personagem (POST)
@router_personagem.post("/")
def create_character(character: Character, username: str = Depends(get_current_user)):
    existing = characters_collection.find_one({
        "nome": character.nome,
        "owner_username": username
    })
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Você já possui um personagem com esse nome"
        )

    character_dict = character.model_dump() 
    character_dict.update({"owner_username": username})

    result = characters_collection.insert_one(character_dict)
    
    created = characters_collection.find_one({"_id": result.inserted_id})
    return json.loads(dumps(created))


#Rota: Listar Personagens (GET)
@router_personagem.get("/")
def get_characters(username: str = Depends(get_current_user)):
    chars = list(characters_collection.find({"owner_username": username}))
    return json.loads(dumps(chars))


#Rota: Obter Personagem por ID (GET)
@router_personagem.get("/{character_id}")
def get_character(character_id: str, username: str = Depends(get_current_user)):
    try:
        char = characters_collection.find_one({
            "_id": ObjectId(character_id),
            "owner_username": username
        })
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    if not char:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return json.loads(dumps(char))


#Rota: Deletar Personagem(DELETE)
@router_personagem.delete("/{character_id}")
def delete_character(character_id: str, username: str = Depends(get_current_user)):
    try:
        result = characters_collection.delete_one({
            "_id": ObjectId(character_id),
            "owner_username": username
        })
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404, 
            detail="Personagem não encontrado ou você não tem permissão"
        )
    return {"message": "Personagem deletado"}

