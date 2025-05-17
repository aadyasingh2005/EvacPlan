

from fastapi import FastAPI
from .routes import router as blueprint_router

app = FastAPI()

app.include_router(blueprint_router, prefix="/api/blueprint")

# Optional root route
@app.get("/")
def read_root():
    return {"message": "Backend 2 - Blueprint Upload API"}
