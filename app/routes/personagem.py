from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
from bson import ObjectId
from app.database import get_personagens_collection
from bson.json_util import dumps
import json
from app.routes.auth import get_current_user

router_personagem = APIRouter(prefix="/personagens", tags=["personagens"])
characters_collection = get_personagens_collection()

client = MongoClient("mongodb://localhost:27017")
db = client["secretproject_db"]
characters_collection = db["personagens"]

class Character(BaseModel):
    name: str
    role: str
    age: int
    image: str = ""
    campaign: bool = False

# Criar personagem
@router_personagem.post("/")
def create_character(character: Character, username: str = Depends(get_current_user)):
    character_dict = character.dict()
    character_dict["owner_username"] = username  # atrela ao usuário
    result = characters_collection.insert_one(character_dict)
    created = characters_collection.find_one({"_id": result.inserted_id})
    return json.loads(dumps(created))

# Listar personagens do usuário logado
@router_personagem.get("/")
def get_characters(username: str = Depends(get_current_user)):
    chars = list(characters_collection.find({"owner_username": username}))
    return json.loads(dumps(chars))

# Deletar personagem (somente dono)
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
