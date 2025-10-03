from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel
from passlib.context import CryptContext
from app.database import get_users_collection
from app.models.UsuarioModel import UsuarioModel, UsuarioLogin

SECRET_KEY = "minhachave123" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60

users_collection = get_users_collection()
router_auth = APIRouter(prefix="/auth", tags=["auth"])

# 🔹 Usando argon2
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)




class ChangePasswordModel(BaseModel):
    current_password: str
    new_password: str




oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ---------------- SIGNUP ----------------
@router_auth.post("/signup")
def register_user(usuario: UsuarioModel):
    if users_collection.find_one({"usuario": usuario.nomeUsuario}):
        raise HTTPException(status_code=400, detail="Usuário já existe")

    hashed_password = hash_password(usuario.senha)
    user = {
        "nome": usuario.nome,
        "usuario": usuario.nomeUsuario,
        "senha": hashed_password
    }
    
    users_collection.insert_one(user)
    return {"msg": "Usuário registrado com sucesso"}

# ---------------- LOGIN ----------------
@router_auth.post("/login")
def realizar_login(login_data: UsuarioLogin):
    user = users_collection.find_one({"usuario": login_data.nomeUsuario})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    hashed_password = user.get("senha")
    if not hashed_password:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Hash da senha inválido no banco")

    # Verifica senha com tratamento seguro
    try:
        if not verify_password(login_data.senha, hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro na verificação da senha: {e}")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.nomeUsuario},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }




# ---------------- PERFIL (GET /auth/me) ----------------
@router_auth.get("/me")
def read_users_me(current_user: str = Depends(get_current_user)):
    user = users_collection.find_one({"usuario": current_user})

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "id": str(user["_id"]),
        "nome": user.get("nome"),
        "usuario": user.get("usuario")
    }


# ---------------- CHANGE PASSWORD ----------------
@router_auth.post("/change-password")
def change_password(
    payload: ChangePasswordModel,
    current_username: str = Depends(get_current_user)
):
    user = users_collection.find_one({"usuario": current_username})
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    hashed_password = user.get("senha")
    if not hashed_password:
        raise HTTPException(status_code=500, detail="Hash de senha ausente no banco")

    # Verifica senha atual
    try:
        if not verify_password(payload.current_password, hashed_password):
            raise HTTPException(status_code=401, detail="Senha atual incorreta")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Erro na verificação da senha: {e}")

    # Valida requisitos mínimos da nova senha (exemplo simples)
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter pelo menos 6 caracteres")

    # Hash e update
    new_hashed = hash_password(payload.new_password)
    result = users_collection.update_one(
        {"usuario": current_username},
        {"$set": {"senha": new_hashed}}
    )
    if result.modified_count != 1:
        raise HTTPException(status_code=500, detail="Não foi possível atualizar a senha")

    return {"msg": "Senha alterada com sucesso"}

