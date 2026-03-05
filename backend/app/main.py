from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, catalog, purchases

app = FastAPI(title="Chinook Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # puedes limitar a tu IP del front si quieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(health.router, prefix="/v1")
app.include_router(catalog.router, prefix="/v1")
app.include_router(purchases.router, prefix="/v1")
