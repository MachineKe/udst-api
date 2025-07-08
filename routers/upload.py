from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
import os

router = APIRouter(
    prefix="/upload",
    tags=["upload"]
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

import uuid
from datetime import datetime
import json

@router.get("/list/")
async def list_uploaded_documents():
    # List all JSON files in the uploads directory and return their content
    docs = []
    for fname in os.listdir(UPLOAD_DIR):
        if fname.endswith(".json"):
            with open(os.path.join(UPLOAD_DIR, fname), "r", encoding="utf-8") as f:
                doc = json.load(f)
                docs.append(doc)
    return {"documents": docs}

@router.post("/")
async def upload_pdfs(files: List[UploadFile] = File(...)):
    if not (1 <= len(files) <= 2):
        raise HTTPException(status_code=400, detail="You must upload one or two PDF files.")

    extracted_docs = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{file.filename} is not a PDF file.")
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Simulate extraction (replace with real extraction logic)
        doc_id = str(uuid.uuid4())
        extracted_doc = {
            "id": doc_id,
            "fileName": file.filename,
            "fileType": file.content_type,
            "fileSize": os.path.getsize(file_path),
            "uploadDate": datetime.utcnow().isoformat(),
            "extractedText": "Simulated extracted text.",
            "metadata": {
                "wordCount": 100,
                "characterCount": 600,
                "pageCount": 2,
                "language": "en",
                "author": "Unknown",
                "title": file.filename,
                "subject": "",
                "creator": "",
                "creationDate": datetime.utcnow().isoformat(),
                "modificationDate": datetime.utcnow().isoformat(),
            },
            "tables": [],
            "images": [],
            "structure": {
                "headings": [],
                "paragraphs": [],
                "lists": [],
            },
            "processingStatus": "completed",
            "processingTime": 1000,
            "accuracy": 95.0,
            "errors": [],
        }
        # Save extracted data as JSON file
        with open(os.path.join(UPLOAD_DIR, f"{doc_id}.json"), "w", encoding="utf-8") as jf:
            json.dump(extracted_doc, jf, ensure_ascii=False, indent=2)
        extracted_docs.append(extracted_doc)

    return {"documents": extracted_docs}

@router.post("/compare/")
async def compare_documents(doc1_id: str, doc2_id: str):
    # Load extracted data for both documents from disk
    doc1_path = os.path.join(UPLOAD_DIR, f"{doc1_id}.json")
    doc2_path = os.path.join(UPLOAD_DIR, f"{doc2_id}.json")
    if not os.path.exists(doc1_path) or not os.path.exists(doc2_path):
        raise HTTPException(status_code=404, detail="One or both documents not found for comparison.")

    with open(doc1_path, "r", encoding="utf-8") as f1, open(doc2_path, "r", encoding="utf-8") as f2:
        doc1 = json.load(f1)
        doc2 = json.load(f2)

    # Simulate comparison logic
    comparison_result = {
        "doc1Id": doc1_id,
        "doc2Id": doc2_id,
        "similarityScore": 0.85,
        "differences": [
            {"field": "wordCount", "doc1": doc1["metadata"]["wordCount"], "doc2": doc2["metadata"]["wordCount"]},
            {"field": "characterCount", "doc1": doc1["metadata"]["characterCount"], "doc2": doc2["metadata"]["characterCount"]},
            {"field": "extractedText", "doc1": doc1["extractedText"], "doc2": doc2["extractedText"]},
        ],
        "summary": "Documents are 85% similar. Main differences are in word count and extracted text.",
    }
    return {"result": comparison_result}
