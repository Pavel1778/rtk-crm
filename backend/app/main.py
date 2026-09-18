from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, create_tables
from app.core.config import settings
from app.api import auth, interactions, workflow, catalogs

app = FastAPI(title=settings.APP_NAME)

# CORS
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Init DB
init_db(settings.DATABASE_URL)

@app.on_event("startup")
async def on_startup():
    await create_tables()

@app.get("/")
async def root():
    return {"status": "ok", "message": "RTK CRM API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(interactions.router, prefix="/api/v1/interactions", tags=["Interactions"])
app.include_router(workflow.router, prefix="/api/v1/workflow", tags=["Workflow"])
app.include_router(catalogs.router, prefix="/api/v1/catalogs", tags=["Catalogs"])
