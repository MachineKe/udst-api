from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import os

router = APIRouter(
    prefix="/upload",
    tags=["upload"]
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    if not (1 <= len(files) <= 2):
        raise HTTPException(status_code=400, detail="You must upload one or two PDF files.")

    saved_files = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF file.")
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_files.append(file_path)

    # Extraction and DB logic will be added here
    return {"message": "Files uploaded successfully.", "files": saved_files}
