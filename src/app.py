from fastapi import FastAPI

from src.config import settings
from src.api.endpoints.v1.auth import router as auth_router
from src.api.endpoints.v1.vendors import router as vendors_router
from src.api.endpoints.v1.products import router as products_router
from src.api.endpoints.v1.categories import router as categories_router
from src.api.endpoints.v1.orders import router as orders_router
from src.api.endpoints.v1.carts import router as carts_router
from src.api.endpoints.v1.wallets import router as wallets_router

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

app.include_router(
    auth_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    vendors_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    products_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    categories_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    orders_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    carts_router,
    prefix=settings.API_V1_PREFIX,
)

app.include_router(
    wallets_router,
    prefix=settings.API_V1_PREFIX,
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}