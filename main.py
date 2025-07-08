from fastapi import FastAPI
from routers import upload

app = FastAPI(
    title="DocCompare Analytics API",
    description="Backend API for document upload, extraction, comparison, and analytics.",
    version="0.1.0"
)

app.include_router(upload.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to DocCompare Analytics API"}
