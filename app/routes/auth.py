from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta, datetime
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.database import get_users_collection
from app.models.UsuarioModel import UsuarioModel, UsuarioLogin

SECRET_KEY = "sua_chave_super_secreta_aqui" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60

users_collection = get_users_collection()
router_auth = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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

@router_auth.post("/login")
def realizar_login(login_data: UsuarioLogin):
    user = users_collection.find_one({"usuario": login_data.nomeUsuario})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    if not verify_password(login_data.senha, user["senha"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")


    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": login_data.nomeUsuario},
        expires_delta=access_token_expires
    )

    print("Senha:", login_data.senha)
    print("Hash banco:", user["senha"])
    print("igual:", verify_password(login_data.senha, user["senha"]))

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

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
