
from fastapi import FastAPI
from routers.alerts import router as alerts_router
from routers.accounts import router as accounts_router
from routers.knowledge import router as knowledge_router
from dotenv import load_dotenv
from routers.agent_api import router as agent_router

load_dotenv()
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(alerts_router)
app.include_router(accounts_router)
app.include_router(knowledge_router)
app.include_router(agent_router)