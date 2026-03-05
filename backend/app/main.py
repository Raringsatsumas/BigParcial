from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import health, catalog, purchases, auth, admin_tracks, stats

app = FastAPI(title="Chinook Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# opcional sin versión
app.include_router(health.router)

# versionado
app.include_router(health.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(catalog.router, prefix="/v1")
app.include_router(purchases.router, prefix="/v1")
app.include_router(admin_tracks.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
