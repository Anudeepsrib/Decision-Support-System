#!/usr/bin/env python
"""Local API smoke test for the full MVP workflow."""

from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
DEFAULT_ARR = ROOT / "arr_order_test.pdf"
DEFAULT_PETITION = ROOT / "petition_test.pdf"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


ENV = {**parse_env(ENV_FILE), **os.environ}
BACKEND_URL = ENV.get("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
FINANCIAL_YEAR = ENV.get("DEMO_FINANCIAL_YEAR", "2024-25")


def url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BACKEND_URL}{path if path.startswith('/') else '/' + path}"


def request_json(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url(path), data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach backend at {BACKEND_URL}: {exc.reason}") from exc


def request_bytes(path: str) -> bytes:
    try:
        with urllib.request.urlopen(url(path), timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed with {exc.code}: {body}") from exc


def upload_pdf(path: Path, endpoint: str) -> dict:
    if not path.exists():
        raise RuntimeError(f"Missing smoke-test PDF: {path}")

    boundary = f"----kserc-smoke-{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "application/pdf"
    file_bytes = path.read_bytes()
    parts = [
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="financial_year"\r\n\r\n'
        f"{FINANCIAL_YEAR}\r\n",
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n",
    ]
    body = "".join(parts).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        url(endpoint),
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {endpoint} failed with {exc.code}: {body}") from exc


def poll_job(status_url: str, label: str) -> dict:
    deadline = time.time() + 120
    last_stage = ""
    while time.time() < deadline:
        status = request_json(status_url)
        stage = status.get("stage") or status.get("status")
        if stage != last_stage:
            print(f"{label}: {status.get('status')} - {stage}")
            last_stage = stage
        if status.get("status") == "COMPLETED":
            return status
        if status.get("status") == "FAILED":
            raise RuntimeError(f"{label} extraction failed: {status.get('error_message')}")
        time.sleep(1.5)
    raise RuntimeError(f"{label} extraction did not finish within 120 seconds.")


def main() -> int:
    arr_pdf = Path(ENV.get("ARR_PDF", str(DEFAULT_ARR))).resolve()
    petition_pdf = Path(ENV.get("PETITION_PDF", str(DEFAULT_PETITION))).resolve()

    print(f"Backend: {BACKEND_URL}")
    print("Checking /health...")
    health = request_json("/health")
    print(f"Health: {health.get('status')}")

    print(f"Uploading ARR PDF: {arr_pdf.name}")
    arr = upload_pdf(arr_pdf, "/upload/arr")
    poll_job(arr["status_url"], "ARR")

    print(f"Uploading Petition PDF: {petition_pdf.name}")
    petition = upload_pdf(petition_pdf, "/upload/petition")
    poll_job(petition["status_url"], "Petition")

    print("Running comparison...")
    comparison = request_json(f"/comparison/run?financial_year={FINANCIAL_YEAR}", method="POST")
    print(f"Comparison case: {comparison['case_id']} ({comparison['total_items']} items)")

    latest = request_json(f"/comparison/results?financial_year={FINANCIAL_YEAR}")
    if latest["case_id"] != comparison["case_id"]:
        raise RuntimeError("Latest comparison endpoint returned a different case.")

    print("Generating report...")
    order = request_json(
        "/report/generate",
        method="POST",
        payload={
            "case_id": comparison["case_id"],
            "financial_year": comparison["financial_year"],
            "officer_name": "Smoke Test",
        },
    )
    pdf = request_bytes(f"/report/{order['id']}")
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("Report download did not return a PDF.")

    print(f"Report generated: {order['id']} ({len(pdf)} bytes)")
    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
