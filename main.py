from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload

app = FastAPI(
    title="DocCompare Analytics API",
    description="Backend API for document upload, extraction, comparison, and analytics.",
    version="0.1.0"
)

# Allow frontend dev server for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to DocCompare Analytics API"}
