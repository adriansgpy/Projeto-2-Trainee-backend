from pymongo import MongoClient

try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    print("Conectado ao MongoDB")
except Exception as e:
    print("Erro de conexão:", e)

