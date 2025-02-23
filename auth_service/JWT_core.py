from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = "fhjjahfjjhwjehfu29357u93ujrfikw3ht980034yhi9082" # Лучше брать из переменных окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
