from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import boto3
import tempfile
import os
import io

load_dotenv()  # loads .env for local dev; no-op in production with IAM role

from extractor import extract_resume_text
from llm import extract_structured_data
from renderer import render_resume

app = FastAPI(title="My Resume backend",version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

S3_BUCKET = "exavalu-resume-storage"
S3_UPLOADS_FOLDER = "uploads"
S3_PROCESSED_FOLDER = "processed"

s3 = boto3.client("s3")  # uses AWS credentials from environment / IAM role


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    safe_filename = os.path.basename(file.filename)
    original_stem = os.path.splitext(safe_filename)[0]
    output_filename = f"{original_stem}_EV_Format.docx"

    file_bytes = await file.read()

    # --- Upload original resume to S3 uploads/ ---
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_UPLOADS_FOLDER}/{safe_filename}",
        Body=file_bytes,
        ContentType=file.content_type or "application/octet-stream",
    )

    # --- Extract text using a temp file (extractor needs a file path) ---
    suffix = os.path.splitext(safe_filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        extracted_text = extract_resume_text(tmp_path)
    finally:
        os.remove(tmp_path)  # always clean up

    # --- LLM extraction ---
    structured_data = extract_structured_data(extracted_text)

    # --- Render docx into a temp file, then read back into memory ---
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_out:
        tmp_out_path = tmp_out.name

    try:
        render_resume(
            structured_data,
            "templates/resume_template.docx",
            tmp_out_path,
        )
        with open(tmp_out_path, "rb") as f:
            output_bytes = f.read()
    finally:
        os.remove(tmp_out_path)  # always clean up

    # --- Upload rendered docx to S3 processed/ ---
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_PROCESSED_FOLDER}/{output_filename}",
        Body=output_bytes,
        ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    # --- Stream the file directly back to the caller ---
    return StreamingResponse(
        content=io.BytesIO(output_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"'
        },
    )