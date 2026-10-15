from fastapi import FastAPI  # Import the class used to create the API application.

from routers import firms, insight, people, knowledge  # Import the route modules so their endpoints can be registered on the application.
from routers.agent_api import router as agent_router
from knowledge_store import build_index  # Build the same index used by the endpoints and agent.


app = FastAPI(title="Firm Intelligence API")  # Create the FastAPI application and set its documentation title.


@app.on_event("startup")  # Register this function to run during application startup.
def startup_event():  # Run this function when the application starts.
    build_index()  # Embed the documents and build the in-memory index during startup.


app.include_router(firms.router)  # Add the firms routes to the application.
app.include_router(people.router)  # Add the people routes to the application.
app.include_router(insight.router)  # Add the insight routes to the application.
app.include_router(knowledge.router)  # Add the knowledge routes to the application.
app.include_router(agent_router)


@app.get("/health")  # Register the following function as the handler for this GET route.
def health():  # Provide a basic application health response.
    return {"status": "ok"}  # Return {"status": "ok"} to the caller.
