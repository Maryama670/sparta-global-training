from dotenv import load_dotenv

load_dotenv(".env.local")

from fastapi import FastAPI
from routers.firms import router as firms_router
from routers.people import router as people_router
from routers.insight import router as insights_router
from routers.knowledge import router as knowledge_router
from routers.agent import router as agent_router

app = FastAPI(title="Firm Inteligence API")

app.include_router(firms_router)
app.include_router(people_router)
app.include_router(insights_router)
app.include_router(knowledge_router)
app.include_router(agent_router)

@app.get("/health")
def health():
    return {"status":"ok"}