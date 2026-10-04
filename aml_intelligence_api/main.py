from fastapi import FastAPI
from routers.alerts import router as alerts_router

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(alerts_router)