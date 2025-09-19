from jose import jwt

SECRET_KEY = "sua_chave_super_secreta_aqui"
ALGORITHM = "HS256"

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0ZSIsImV4cCI6MTc1ODEwNjk0OX0.Sx80h8dxZ1EJ_GoBi1_5-Ph5c9NAbl-ltR32xUrzLxU"

payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
print(payload)
