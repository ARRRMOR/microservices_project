from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
import httpx
import models, database, JWT_core


database.init_db()

SECRET_KEY = "fhjjahfjjhwjehfu29357u93ujrfikw3ht980034yhi9082"
ALGORITHM = ["HS256"]
SECRET_TOKEN = "rtn432573n5275ntou78p78"

app = FastAPI()

PRODUCT_SERVICE_URL = 'http://product_service:8000'

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    username: str
    password: str
    company: str
    tg_id: int
    email: str

class UserLogin(BaseModel):
    username: str
    password: str

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if not user.username or not user.password or not user.company or not user.email:
        raise HTTPException(status_code=400, detail="Both username and password are required, also company name.")
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="Username already registered")
    hashed_password = pwd_context.hash(user.password)
    new_user = models.User(username=user.username, password=hashed_password, company=user.company,
                           tg_id=user.tg_id, email=user.email)
    db.add(new_user)
    db.commit()
    return {"message": "User created successfully"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Both username and password are required")
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    # Генерация токена
    access_token = JWT_core.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/profile/{id}")
def get_profile(id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)):

    try:
        response = httpx.get(f"{PRODUCT_SERVICE_URL}/products/get_products_ids/{id}", headers={"Authorization": f"Bearer {SECRET_TOKEN}"})
        response.raise_for_status()
        products = response.json()
    except:
        raise HTTPException(status_code=404, detail="Not Found")

    user_profile = db.query(models.User).filter(models.User.id == id).first()
    if user_profile.username != user:
        raise HTTPException(status_code=404, detail="Dont have acess to this user")

    if not user_profile:
        raise HTTPException(status_code=404, detail="User not found")

    return {"username": user_profile.username,
            "company": user_profile.company,
            "products": [{"product": item["name"], "price": item["price"], "amount": item["amount"]} for item in products]
            }


@app.get("/profile/get_id/{username}")
def get_id(username: str, db: Session = Depends(get_db)):
    if not username:
        raise HTTPException(status_code=404, detail="User not found")

    user = db.query(models.User).filter(models.User.username == username).first()
    return {"id": user.id}














