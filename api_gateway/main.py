from fastapi import FastAPI, HTTPException, Header
import httpx
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

#url - адреса сервисов

AUTH_SERVICE_URL = 'http://auth_service:8000'
PRODUCT_SERVICE_URL = 'http://product_service:8000'
CART_SERVICE_URL = 'http://cart_service:8000'
ALLOWED_PATHS = {'register', 'login'}



@app.get("/product/{product_id}")
async def product_proxy(product_id: int, authorization: str = Header(...)):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}", headers={'Authorization': f'Bearer {authorization}'})
            response.raise_for_status()  # Проверяем статус ответа
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Product service error")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/product/create")
async def new_product_proxy(data: dict, authorization: str = Header(...)):
    logger.info(f'token is {authorization}')
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{PRODUCT_SERVICE_URL}/new", json=data, headers={'Authorization': f'Bearer {authorization}'})
        return response.json()

@app.post("/auth/{path:path}")
async def auth_proxy_post(path: str, data: dict):
    if path not in ALLOWED_PATHS:
        raise HTTPException(status_code=404, detail="URL_NOT_FOUND")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{AUTH_SERVICE_URL}/{path}", json=data)
        return response.json()

@app.get("/profile/{id}")
async def profile_proxy(id: int, authorization: str = Header(...)):
    if not id:
        raise HTTPException(status_code=404, detail="USER_ID_NOT_FOUND")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{AUTH_SERVICE_URL}/profile/{id}", headers={'Authorization': f'Bearer {authorization}'})
        return response.json()

@app.post("/cart/add")
async def add_to_cart_proxy(data: dict, authorization: str = Header(...)):
    if not data:
        raise HTTPException(status_code=404, detail="EMPTY_DATA")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CART_SERVICE_URL}/cart/add_item", json=data, headers={'Authorization': f'Bearer {authorization}'})
        return response.json()

@app.get("/cart")
async def add_to_cart_proxy(authorization: str = Header(...)):
    if not authorization:
        raise HTTPException(status_code=404, detail="EMPTY_Header")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CART_SERVICE_URL}/get_cart", headers={'Authorization': f'Bearer {authorization}'})
        return response.json()


@app.post("/cart")
async def remove_cart_proxy(data: dict, authorization: str = Header(...)):
    if not authorization:
        raise HTTPException(status_code=404, detail="EMPTY_Header")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CART_SERVICE_URL}/cart/remove", json=data, headers={'Authorization': f'Bearer {authorization}'})
        return response.json()

@app.post("/cart/buy")
async def remove_cart_proxy(authorization: str = Header(...)):
    if not authorization:
        raise HTTPException(status_code=404, detail="EMPTY_Header")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{CART_SERVICE_URL}/cart/checkout", headers={'Authorization': f'Bearer {authorization}'})
        return response.json()






