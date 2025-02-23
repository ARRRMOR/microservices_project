from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import redis
import json
import os
import httpx
from jose import JWTError, jwt
import pika
from typing import List

app = FastAPI()

AUTH_SERVICE_URL = 'http://auth_service:8000'

SECRET_KEY = "fhjjahfjjhwjehfu29357u93ujrfikw3ht980034yhi9082"
ALGORITHM = ["HS256"]

# Настройка подключения к Redis через переменную окружения
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://shkibidi:pokazal@rabbitmq:5672/")


class CartItem(BaseModel):
    product_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    username: int

class ToRemoveList(BaseModel):
    toremove: List[int]

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


def send_to_rabbitmq(queue, message: dict):
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))

    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)

    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Сообщения сохраняются (не теряются при сбое)
        ),
    )
    connection.close()


@app.post("/cart/add_item")
def cart_add(item: CartItem, user: str = Depends(get_current_user)):
    key = f"Cart:{user}"
    cart_data = r.get(key)
    if cart_data:
        try:
            cart = json.loads(cart_data)
        except json.JSONDecodeError:
            cart = []
    else:
        cart = []

    found = False
    for cart_item in cart:
        if cart_item["product_id"] == item.product_id:
            cart_item["quantity"] += item.quantity
            found = True
            break
    if not found:
        cart.append(item.dict())

    r.set(key, json.dumps(cart))
    return {"message": "Item added to cart", "cart": cart}

@app.get("/get_cart")
def get_cart(user: str = Depends(get_current_user)):

    key = f"Cart:{user}"
    cart_data = r.get(key)
    if not cart_data:
        return {"cart": []}
    try:
        cart = json.loads(cart_data)
    except json.JSONDecodeError:
        cart = []
    return {"cart": cart}

@app.post("/cart/remove")
def remove_cart(to_remove_list: ToRemoveList, user: str = Depends(get_current_user)):
    key = f"Cart:{user}"
    cart_data = r.get(key)
    if not cart_data:
        raise HTTPException(status_code=404, detail="CART IS EMPTY")
    try:
        cart = json.loads(cart_data)
    except json.JSONDecodeError:
        return HTTPException(status_code=500, detail="Invalid cart data")

    new_cart = [i for i in cart if i["product_id"] not in to_remove_list.toremove]
    r.set(key, json.dumps(new_cart))
    return {"message":"Item removed", "cart": new_cart}

@app.post("/cart/checkout")
def checkout(user: str = Depends(get_current_user)):
    key = f"Cart:{user}"
    cart_data = r.get(key)
    if not cart_data:
        raise HTTPException(status_code=404, detail="CART IS EMPTY")
    try:
        cart = json.loads(cart_data)
    except json.JSONDecodeError:
        return HTTPException(status_code=500, detail="Invalid cart data")
    message = {"username": user, "items": cart}
    send_to_rabbitmq("checkout_queue", message)
    r.delete(key)
    return {"message": "Order placed successfully"}























