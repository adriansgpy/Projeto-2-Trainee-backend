from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")

db = client["secretproject_db"]

def get_users_collection():
    return db["usuarios"]


def get_personagens_collection():
    return db["personagens"]

