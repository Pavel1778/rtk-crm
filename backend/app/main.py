from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.universities import router as universities_router
import os

app = FastAPI(
    title="RTK CRM API",
    description="CRM для ИТ Школы Ростелекома",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(universities_router)


@app.get("/")
async def root():
    return {"message": "RTK CRM API", "status": "ok", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
