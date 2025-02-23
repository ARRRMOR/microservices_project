from fastapi import FastAPI, HTTPException, Depends, Header
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from sqlalchemy import text
from jose import jwt, JWTError
from pydantic import BaseModel
import httpx
import database
import logging
import aio_pika
import asyncio
import os
import json
import redis.asyncio as aioredis


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

database.init_db()

SECRET_KEY = "fhjjahfjjhwjehfu29357u93ujrfikw3ht980034yhi9082"
ALGORITHM = ["HS256"]
SECRET_TOKEN = "rtn432573n5275ntou78p78"

connection = None
channel = None

app = FastAPI()

redis_client = None

AUTH_SERVICE_URL = 'http://auth_service:8000'

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://shkibidi:pokazal@rabbitmq:5672/")

# Настройка подключения к Redis через переменную окружения
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")


class ProductCreate(BaseModel):
    name: str
    price: float
    amount: int


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with database.AsyncSessionLocal() as db:
        yield db

def get_current_user(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]
        logger.info(f'token is {token}')
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        logger.info(f'payload is {payload}')
        username: str = payload.get("sub")
        logger.info(f'username is {username}')
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def connection_to_rabbitmq():
    global connection, channel
    while connection is None:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            channel = await connection.channel()
            logger.info(f"✅ Connected to RabbitMQ: {connection}")
        except Exception as e:
            logger.info(f"🔄 Waiting for RabbitMQ... {e}, connection: {connection}")
            await asyncio.sleep(5)  # Подождать перед новой попыткой
async def on_message(message: aio_pika.IncomingMessage):
    async with message.process():
        message_body = json.loads(message.body.decode('utf-8'))
        logger.info(f'message_body is {message_body}')
        username = message_body['username']
        items = message_body['items']

        db = database.SessionLocal()

        try:
            for item in items:
                product_id = item["product_id"]
                amount_to_buy = item["quantity"]

                # Получаем товар из базы данных
                product = db.query(database.Product).filter(database.Product.id == product_id).first()

                if not product:
                    logger.warning(f"Product with ID {product_id} not found.")
                    continue

                # Проверяем наличие товара на складе
                if product.amount < amount_to_buy:
                    logger.warning(f"Not enough stock for product {product_id}.")
                    continue

                # Обновляем количество товара
                product.amount -= amount_to_buy
                db.commit()
                logger.info(f"Product {product_id} stock updated. Remaining amount: {product.amount}")

        except Exception as e:
            db.rollback()
            logger.error(f"Error processing checkout: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
        finally:
            db.close()

async def listen_to_queue():
    await connection_to_rabbitmq()

    queue = await channel.declare_queue('checkout_queue', durable=True)
    await queue.consume(on_message)

    logger.info("Started listening rabbitmq")
    await asyncio.Future()

@app.on_event("startup")
async def startup():
    asyncio.create_task(listen_to_queue())
    global redis_client
    redis_client = await aioredis.Redis.from_url(REDIS_URL, decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    await redis_client.close()

# Эндпоинты
@app.get('/products/{product_id}')
async def get_product(product_id: int, db: AsyncSession = Depends(async_get_db), user: str = Depends(get_current_user)):

    cache_key = f"product:{product_id}"

    cached_product = await redis_client.get(cache_key)
    if cached_product:
        return json.loads(cached_product)

    result = await db.execute(
        text("SELECT id, name, price, amount, owner_id FROM products WHERE id = :id"),
        {"id": product_id}
    )
    product = result.mappings().first()
    product = dict(product)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Кладем в Redis (асинхронно)
    await redis_client.setex(cache_key, 30, json.dumps(product))
    logger.info(f"product is : {product}")
    return product

@app.post('/new')
def create_product(product: ProductCreate, db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    try:
        response = httpx.get(f"{AUTH_SERVICE_URL}/profile/get_id/{user}")
    except:
        raise HTTPException(status_code=404, detail="Not Found")
    response = response.json()
    new_product = database.Product(name=product.name, price=product.price,
                                   amount=product.amount, owner_id=response.get("id"))

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"id": new_product.id, "name": new_product.name, "price": new_product.price,
            "amount": new_product.amount, "owner_id": new_product.owner_id}

@app.get("/products/get_products_ids/{owner_id}")
def get_owners_products_ids(owner_id: int, db: Session = Depends(get_db), authorization: str = Header(None)):
    print(f"Received access_token: {authorization}")
    if authorization != f"Bearer {SECRET_TOKEN}":
        raise HTTPException(status_code=403, detail="Unauthorized access")
    response_data = db.query(database.Product.name, database.Product.price, database.Product.amount).filter(database.Product.owner_id == owner_id).all()
    response_data = [{"name": name, "price": price, "amount": amount} for name, price, amount in response_data]
    return response_data


















