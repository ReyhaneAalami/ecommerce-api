from fastapi import FastAPI

from src.config import settings
from src.api.endpoints.v1.auth import router as auth_router
from src.api.endpoints.v1.vendors import router as vendors_router
from src.api.endpoints.v1.products import router as products_router
from src.api.endpoints.v1.categories import router as categories_router
from src.api.endpoints.v1.orders import router as orders_router
from src.api.endpoints.v1.carts import router as carts_router
from src.api.endpoints.v1.wallets import router as wallets_router
from src.api.endpoints.v1.payments import router as payments_router

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

for router in (
    auth_router, vendors_router, products_router, categories_router,
    orders_router, carts_router, wallets_router, payments_router,
):
    app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
