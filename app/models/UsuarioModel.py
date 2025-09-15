from pydantic import BaseModel

class UsuarioModel(BaseModel):

    nomeUsuario: str
    nome: str
    senha: str

class Config:
    orm_mode = True

class UsuarioLogin(BaseModel):
    nomeUsuario: str
    senha: str

class UsuarioResponse(BaseModel):
    id: str | None = None
    nomeUsuario: str
    nome: str

    class Config:
        orm_mode = True