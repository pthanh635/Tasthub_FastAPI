from fastapi import FastAPI

from app.api.v1.routers import tasks

app = FastAPI(
    title="TaskHub API",
    description="Day 1: FastAPI layered architecture with an in-memory Task CRUD",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tasks.router, prefix="/api/v1")
