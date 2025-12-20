from fastapi import FastAPI
from app.routes import health, analyze

app = FastAPI()

app.include_router(health.router)
app.include_router(analyze.router)
