#imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router_auth
from app.routes.personagem import router_personagem
from app.routes.llm_service import llm_router
app = FastAPI()

origins = [
    "http://localhost:4200",
]

#Inicialização da API modularizada

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router_auth)
app.include_router(router_personagem)
app.include_router(llm_router)