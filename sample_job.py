import io
import json
import os
import zipfile
from pathlib import Path
from urllib import request

import fitz

base_url = "http://localhost:8000"

sample_a = Path("/data/sampleA")
sample_b = Path("/data/sampleB")
sample_a.mkdir(parents=True, exist_ok=True)
sample_b.mkdir(parents=True, exist_ok=True)

def make_pdf(path: Path, text: str):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=14)
    doc.save(path)
    doc.close()

make_pdf(sample_a / "doc1.pdf", "Sample A - page 1")
make_pdf(sample_b / "doc1.pdf", "Sample B - page 1 (changed)")

zip_a = Path("/data/sampleA.zip")
zip_b = Path("/data/sampleB.zip")

def make_zip(src_dir: Path, zip_path: Path):
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in src_dir.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(src_dir).as_posix())

make_zip(sample_a, zip_a)
make_zip(sample_b, zip_b)

def json_request(method, url, data=None, headers=None):
    headers = headers or {}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=body, headers=headers, method=method)
    with request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

login = json_request("POST", f"{base_url}/auth/login", {
    "email": os.getenv("SEED_USER_EMAIL", "user@example.com"),
    "password": os.getenv("SEED_USER_PASSWORD", "user123")
})
access = login["access_token"]

job = json_request("POST", f"{base_url}/jobs", headers={"Authorization": f"Bearer {access}"})
job_id = job["id"]

def upload_zip(job_id, set_name, zip_path: Path):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open(zip_path, "rb") as f:
        file_bytes = f.read()
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(b"Content-Disposition: form-data; name=\"zip_file\"; filename=\"payload.zip\"\r\n")
    body.write(b"Content-Type: application/zip\r\n\r\n")
    body.write(file_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    data = body.getvalue()

    req = request.Request(
        f"{base_url}/jobs/{job_id}/upload?set={set_name}",
        data=data,
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with request.urlopen(req) as resp:
        resp.read()

upload_zip(job_id, "A", zip_a)
upload_zip(job_id, "B", zip_b)

json_request("POST", f"{base_url}/jobs/{job_id}/start", headers={"Authorization": f"Bearer {access}"})

print(f"JOB_ID={job_id}")
