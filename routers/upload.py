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

@router.get("/{doc_id}")
async def get_document_by_id(doc_id: str):
    # Return the extracted data for a single document by ID
    doc_path = os.path.join(UPLOAD_DIR, f"{doc_id}.json")
    if not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Document not found.")
    with open(doc_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return {"document": doc}

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

        # Extract tables using pdfplumber (regardless of OCR/text extraction)
        tables = []
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        # Convert table to a list of rows (each row is a list of cell values)
                        tables.append(table)
        except Exception as e:
            print(f"Table extraction failed for {file.filename}: {e}")

        # Fallback to OCR with EasyOCR if PyPDF2 fails or returns no text
        if not extracted_text:
            try:
                import pdfplumber
                import easyocr
                ocr_reader = easyocr.Reader(['en'])
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        print(f"Running EasyOCR on page {i+1} of {len(pdf.pages)}...")
                        img = page.to_image(resolution=200)
                        import numpy as np
                        np_image = np.array(img.original)
                        # Use detail=1 to get bounding box data
                        ocr_results = ocr_reader.readtext(np_image, detail=1, paragraph=False)
                        # Group words by line (y coordinate)
                        from collections import defaultdict
                        line_dict = defaultdict(list)
                        for bbox, text, conf in ocr_results:
                            # bbox: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                            y_center = (bbox[0][1] + bbox[2][1]) / 2
                            line_dict[round(y_center, 0)].append((bbox[0][0], text))
                        # Sort lines by y, then words by x
                        for y in sorted(line_dict.keys()):
                            words = sorted(line_dict[y], key=lambda x: x[0])
                            # Insert enough spaces between words to simulate columns
                            line = ""
                            prev_x = None
                            for x, word in words:
                                if prev_x is not None:
                                    # Add spaces proportional to distance between words
                                    gap = int((x - prev_x) // 15)
                                    line += " " * max(1, gap)
                                line += word
                                prev_x = x + len(word) * 10  # crude estimate of word width
                            extracted_text += line + "\n"
                print(f"Extracted text length for {file.filename} (EasyOCR): {len(extracted_text)}")
            except Exception as e:
                print(f"OCR extraction failed for {file.filename} (EasyOCR): {e}")

        # Always attempt to extract tables from extracted_text and merge with any found tables
        if extracted_text:
            def parse_tables_from_text(text):
                import re
                lines = [line for line in text.splitlines() if line.strip()]
                tables_from_text = []
                current_table = []
                col_counts = []
                for line in lines:
                    # Try splitting by 2+ spaces or tab
                    cells = re.split(r"\s{2,}|\t", line.strip())
                    # If not enough columns, try splitting by single space
                    if len(cells) <= 1:
                        cells = [c for c in line.strip().split(" ") if c]
                    # If still not enough, try splitting by comma
                    if len(cells) <= 1 and "," in line:
                        cells = [c.strip() for c in line.split(",")]
                    # Heuristic: consider as table row if 2+ columns and at least one cell is not empty
                    if len(cells) > 1 and any(cell.strip() for cell in cells):
                        col_counts.append(len(cells))
                        # If previous rows had a different column count, allow for some raggedness (tolerance of 1)
                        if current_table:
                            prev_cols = max(set(col_counts[-3:]), key=col_counts[-3:].count) if len(col_counts) >= 3 else col_counts[-1]
                            if abs(len(cells) - prev_cols) > 1:
                                if len(current_table) > 1:
                                    tables_from_text.append(current_table)
                                current_table = []
                                col_counts = [len(cells)]
                        current_table.append(cells)
                    else:
                        if current_table:
                            if len(current_table) > 1:
                                tables_from_text.append(current_table)
                            current_table = []
                            col_counts = []
                if current_table and len(current_table) > 1:
                    tables_from_text.append(current_table)
                return tables_from_text
            tables_from_text = parse_tables_from_text(extracted_text)
            # Merge: only add tables that are not already present (by header row)
            def table_header(table):
                return tuple(str(cell).strip().lower() for cell in table[0]) if table and len(table) > 0 else tuple()
            existing_headers = {table_header(t) for t in tables}
            for t in tables_from_text:
                if table_header(t) not in existing_headers:
                    tables.append(t)

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
            "tables": tables,
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

    # --- Extracted Text Similarity and Diff ---
    import difflib
    text1 = doc1.get("extractedText", "") or ""
    text2 = doc2.get("extractedText", "") or ""
    seq = difflib.SequenceMatcher(None, text1, text2)
    text_similarity = seq.ratio()
    text_diff = list(difflib.unified_diff(
        text1.splitlines(), text2.splitlines(),
        fromfile="doc1", tofile="doc2", lineterm=""
    ))
    differences.append({
        "field": "extractedText",
        "similarity": text_similarity,
        "diff": text_diff[:200],  # Limit diff lines for response size
    })

    # --- Table Comparison ---
    def parse_tables_from_text(text):
        import re
        lines = [line for line in text.splitlines() if line.strip()]
        tables_from_text = []
        current_table = []
        last_col_count = None
        for line in lines:
            cells = re.split(r"\s{2,}|\t", line.strip())
            if len(cells) > 1 and any(cell.strip() for cell in cells):
                if last_col_count is not None and len(cells) != last_col_count and current_table:
                    if len(current_table) > 1:
                        tables_from_text.append(current_table)
                    current_table = []
                current_table.append(cells)
                last_col_count = len(cells)
            else:
                if current_table:
                    if len(current_table) > 1:
                        tables_from_text.append(current_table)
                    current_table = []
                last_col_count = None
        if current_table and len(current_table) > 1:
            tables_from_text.append(current_table)
        return tables_from_text

    tables1 = doc1.get("tables") if "tables" in doc1 else []
    doc1_tables_fallback = False
    extracted_text1 = doc1.get("extractedText", "")
    print(f"[COMPARE] doc1 tables: {tables1} (type: {type(tables1)}), extractedText length: {len(extracted_text1)}")
    if (not tables1 or (isinstance(tables1, list) and len(tables1) == 0)):
        if extracted_text1 and extracted_text1.strip():
            print(f"[COMPARE] Fallback: extracting tables from extractedText for doc1 ({doc1.get('id', 'unknown')})")
            tables1 = parse_tables_from_text(extracted_text1)
            print(f"[COMPARE] Extracted {len(tables1)} tables for doc1 fallback")
            doc1["tables"] = tables1
            doc1_tables_fallback = True
        else:
            print(f"[COMPARE] Skipping fallback for doc1: extractedText is empty or whitespace")
    tables2 = doc2.get("tables") if "tables" in doc2 else []
    doc2_tables_fallback = False
    extracted_text2 = doc2.get("extractedText", "")
    print(f"[COMPARE] doc2 tables: {tables2} (type: {type(tables2)}), extractedText length: {len(extracted_text2)}")
    if (not tables2 or (isinstance(tables2, list) and len(tables2) == 0)):
        if extracted_text2 and extracted_text2.strip():
            print(f"[COMPARE] Fallback: extracting tables from extractedText for doc2 ({doc2.get('id', 'unknown')})")
            tables2 = parse_tables_from_text(extracted_text2)
            print(f"[COMPARE] Extracted {len(tables2)} tables for doc2 fallback")
            doc2["tables"] = tables2
            doc2_tables_fallback = True
        else:
            print(f"[COMPARE] Skipping fallback for doc2: extractedText is empty or whitespace")

    # Persist fallback tables if extracted
    if doc1_tables_fallback:
        with open(doc1_path, "w", encoding="utf-8") as f1:
            json.dump(doc1, f1, ensure_ascii=False, indent=2)
    if doc2_tables_fallback:
        with open(doc2_path, "w", encoding="utf-8") as f2:
            json.dump(doc2, f2, ensure_ascii=False, indent=2)

    table_diffs = []
    used_doc2 = set()

    def table_header(table):
        # Use first row as header, fallback to empty tuple
        return tuple(str(cell).strip().lower() for cell in table[0]) if table and len(table) > 0 else tuple()

    def table_similarity(t1, t2):
        # Compare headers, then content similarity (Jaccard index of rows)
        h1, h2 = table_header(t1), table_header(t2)
        if not h1 or not h2:
            return 0
        header_score = len(set(h1) & set(h2)) / max(len(h1), len(h2))
        # Compare row sets (excluding header)
        rows1 = set(tuple(str(cell).strip().lower() for cell in row) for row in t1[1:])
        rows2 = set(tuple(str(cell).strip().lower() for cell in row) for row in t2[1:])
        row_score = len(rows1 & rows2) / max(1, len(rows1 | rows2))
        return 0.7 * header_score + 0.3 * row_score

    # Match tables by header/content similarity
    for i, t1 in enumerate(tables1):
        best_score = 0
        best_j = None
        for j, t2 in enumerate(tables2):
            if j in used_doc2:
                continue
            score = table_similarity(t1, t2)
            if score > best_score:
                best_score = score
                best_j = j
        if best_score > 0.5 and best_j is not None:
            # Consider as matched tables
            used_doc2.add(best_j)
            t2 = tables2[best_j]
            # Normalize: compare headers, then sets of rows (excluding header)
            h1, h2 = table_header(t1), table_header(t2)
            rows1 = [tuple(str(cell).strip().lower() for cell in row) for row in t1[1:]]
            rows2 = [tuple(str(cell).strip().lower() for cell in row) for row in t2[1:]]
            # Flatten all cell values for content similarity
            def flatten_cells(table):
                return set(str(cell).strip().lower() for row in table for cell in row)
            flat1 = flatten_cells(t1)
            flat2 = flatten_cells(t2)
            overlap = len(flat1 & flat2)
            total = max(1, len(flat1 | flat2))
            content_similarity = overlap / total
            if h1 == h2 and set(rows1) == set(rows2):
                # Content equivalent, even if order differs
                table_diffs.append({
                    "tableIndexDoc1": i + 1,
                    "tableIndexDoc2": best_j + 1,
                    "header": list(h1),
                    "contentEquivalent": True,
                    "table": t1,
                })
            elif content_similarity > 0.7:
                # Similar content, different structure
                table_diffs.append({
                    "tableIndexDoc1": i + 1,
                    "tableIndexDoc2": best_j + 1,
                    "header1": list(h1),
                    "header2": list(h2),
                    "similarContent": True,
                    "similarityScore": round(content_similarity, 2),
                    "table1": t1,
                    "table2": t2,
                })
            else:
                t1_str = "\n".join([",".join([str(cell) for cell in row]) for row in t1])
                t2_str = "\n".join([",".join([str(cell) for cell in row]) for row in t2])
                diff = list(difflib.unified_diff(
                    t1_str.splitlines(), t2_str.splitlines(),
                    fromfile=f"doc1_table_{i+1}", tofile=f"doc2_table_{best_j+1}", lineterm=""
                ))
                table_diffs.append({
                    "tableIndexDoc1": i + 1,
                    "tableIndexDoc2": best_j + 1,
                    "header": list(h1),
                    "diff": diff[:100],  # Limit diff lines for response size
                })
        else:
            # No match found in doc2
            table_diffs.append({
                "tableIndexDoc1": i + 1,
                "onlyIn": "doc1",
                "header": list(table_header(t1)),
                "table": t1,
            })
    # Any tables in doc2 not matched
    for j, t2 in enumerate(tables2):
        if j not in used_doc2:
            table_diffs.append({
                "tableIndexDoc2": j + 1,
                "onlyIn": "doc2",
                "header": list(table_header(t2)),
                "table": t2,
            })
    if table_diffs:
        differences.append({
            "field": "tables",
            "tableDiffs": table_diffs,
        })

    # Calculate similarity score as percent of matching fields (excluding text similarity)
    total_fields = len(differences) + 1  # +1 to avoid division by zero
    similarity_score = 1.0 - (len(differences) / total_fields)

    summary = (
        f"Documents are {(similarity_score * 100):.1f}% similar. "
        f"Found {len(differences)} differing field(s)."
        if differences else "Documents are identical."
    )
    summary += f" Extracted text similarity: {(text_similarity * 100):.1f}%."

    comparison_result = {
        "doc1Id": doc1_id,
        "doc2Id": doc2_id,
        "similarityScore": similarity_score,
        "textSimilarity": text_similarity,
        "differences": differences,
        "summary": summary,
    }
    return {"result": comparison_result}
