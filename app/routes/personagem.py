from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from app.routes.auth import get_current_user
from bson.json_util import dumps
import json
from typing import List, Optional

router_personagem = APIRouter(prefix="/personagens", tags=["personagens"])

client = MongoClient("mongodb://localhost:27017")
db = client["secretproject_db"]
characters_collection = db["personagens"]

class Character(BaseModel):
    nome: str
    role: str
    hpAtual: int
    stamina: int
    ataqueEspecial: str
    inventario: List[str] = []
    image: Optional[str] = ""

@router_personagem.post("/")
def create_character(character: Character, username: str = Depends(get_current_user)):
    character_dict = character.dict()
    character_dict.update({"owner_username": username})

    result = characters_collection.insert_one(character_dict)
    created = characters_collection.find_one({"_id": result.inserted_id})
    return json.loads(dumps(created))

@router_personagem.get("/")
def get_characters(username: str = Depends(get_current_user)):
    chars = list(characters_collection.find({"owner_username": username}))
    return json.loads(dumps(chars))

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

@router_personagem.patch("/{character_id}")
def update_character(character_id: str, data: dict, username: str = Depends(get_current_user)):
    try:
        result = characters_collection.update_one(
            {"_id": ObjectId(character_id), "owner_username": username},
            {"$set": data}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Personagem não encontrado ou você não tem permissão")

    updated = characters_collection.find_one({"_id": ObjectId(character_id)})
    return json.loads(dumps(updated))
