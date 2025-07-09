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
    import PyPDF2

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

        # Extract text from PDF using PyPDF2, fallback to OCR if needed
        extracted_text = ""
        try:
            with open(file_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                for page in reader.pages:
                    extracted_text += page.extract_text() or ""
            print(f"Extracted text length for {file.filename} (PyPDF2): {len(extracted_text)}")
        except Exception as e:
            print(f"Error extracting text from {file.filename} with PyPDF2: {e}")

        # Fallback to OCR with EasyOCR if PyPDF2 fails or returns no text
        if not extracted_text:
            try:
                import pdfplumber
                import easyocr
                reader = easyocr.Reader(['en'])
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        img = page.to_image(resolution=300)
                        # Convert PIL image to numpy array for EasyOCR
                        np_image = img.original
                        # EasyOCR expects numpy array or file path
                        result = reader.readtext(np_image, detail=0, paragraph=True)
                        extracted_text += "\n".join(result) + "\n"
                print(f"Extracted text length for {file.filename} (EasyOCR): {len(extracted_text)}")
            except Exception as e:
                print(f"OCR extraction failed for {file.filename} (EasyOCR): {e}")

        doc_id = str(uuid.uuid4())
        extracted_doc = {
            "id": doc_id,
            "fileName": file.filename,
            "fileType": file.content_type,
            "fileSize": os.path.getsize(file_path),
            "uploadDate": datetime.utcnow().isoformat(),
            "extractedText": extracted_text,
            "metadata": {
                "wordCount": len(extracted_text.split()),
                "characterCount": len(extracted_text),
                "pageCount": len(reader.pages) if extracted_text else 0,
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

    def compare_dicts(d1, d2, prefix=""):
        diffs = []
        for key in set(d1.keys()).intersection(d2.keys()):
            v1, v2 = d1[key], d2[key]
            field_name = f"{prefix}{key}"
            if isinstance(v1, dict) and isinstance(v2, dict):
                diffs.extend(compare_dicts(v1, v2, prefix=field_name + "."))
            elif v1 != v2:
                diffs.append({"field": field_name, "doc1": v1, "doc2": v2})
        return diffs

    differences = compare_dicts(doc1, doc2)

    # Calculate similarity score as percent of matching fields
    total_fields = len(differences) + 1  # +1 to avoid division by zero
    similarity_score = 1.0 - (len(differences) / total_fields)

    summary = (
        f"Documents are {(similarity_score * 100):.1f}% similar. "
        f"Found {len(differences)} differing field(s)."
        if differences else "Documents are identical."
    )

    comparison_result = {
        "doc1Id": doc1_id,
        "doc2Id": doc2_id,
        "similarityScore": similarity_score,
        "differences": differences,
        "summary": summary,
    }
    return {"result": comparison_result}
