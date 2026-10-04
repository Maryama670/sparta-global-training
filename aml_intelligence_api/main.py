from fastapi import FastAPI
from fastapi import FastAPI
from routers.alerts import router as alerts_router
from routers.accounts import router as accounts_router

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(alerts_router)
app.include_router(accounts_router)