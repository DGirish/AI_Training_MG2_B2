from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psycopg
import requests
from dotenv import load_dotenv

try:
    from fpdf import FPDF
except Exception:  # pragma: no cover
    FPDF = None


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

BASE_URL = os.getenv("VALIDATION_BASE_URL", "http://127.0.0.1:8001")
TOKEN = os.getenv(
    "VALIDATION_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNjA5YWFlOS0yNjYwLTQ4ODYtYWM5Mi1lNzlhZDkzNGEyNzYiLCJlbWFpbCI6ImdpcmlzaC5kYW11bHVyaUBzdGFja3lvbi5jb20iLCJleHAiOjE3NzgzMTQzNDR9.hq-ILgv3B2uKSRTaJ3uteNjzMAlTYP7fNxBcWfxW2Bg",
)
TIMEOUT = float(os.getenv("VALIDATION_HTTP_TIMEOUT", "45"))


@dataclass
class StepResult:
    passed: bool
    evidence: str


@dataclass
class ChecklistReport:
    step1_upload_pdf: StepResult
    step2_ask_question: StepResult
    step3_verify_response_uses_pdf: StepResult
    step4_refresh_and_verify_persistence: StepResult
    step5_db_row_proof: StepResult
    thread_id: str | None
    attachment_id: str | None


def _make_pdf(path: Path) -> None:
    if FPDF is None:
        raise RuntimeError("fpdf2 is required for PDF generation")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.multi_cell(0, 10, "Budget Note: The approved budget is 42000 USD for Project Atlas.")
    pdf.output(str(path))


def _post_json(url: str, payload: dict[str, Any]) -> requests.Response:
    return requests.post(url, json=payload, timeout=TIMEOUT)


def _extract_latest_message(messages: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    filtered = [msg for msg in messages if msg.get("role") == role]
    if not filtered:
        return None
    return filtered[-1]


def run() -> ChecklistReport:
    temp_dir = ROOT / ".temp"
    temp_dir.mkdir(exist_ok=True)
    pdf_path = temp_dir / "five_step_budget.pdf"
    _make_pdf(pdf_path)

    thread_id: str | None = None
    attachment_id: str | None = None

    # Step 1: upload PDF
    step1 = StepResult(False, "not_run")
    create_resp = _post_json(
        f"{BASE_URL}/api/threads?token={TOKEN}",
        {"title": "5-step PDF validation"},
    )
    if create_resp.ok:
        thread_id = create_resp.json().get("id")
    if thread_id:
        with pdf_path.open("rb") as file_obj:
            files = {"files": (pdf_path.name, file_obj, "application/pdf")}
            upload_resp = requests.post(
                f"{BASE_URL}/api/chat/attachments/upload?thread_id={thread_id}&token={TOKEN}",
                files=files,
                timeout=TIMEOUT,
            )
        if upload_resp.ok:
            payload = upload_resp.json()
            ids = payload.get("attachment_ids") or []
            if ids:
                attachment_id = ids[0]
                step1 = StepResult(True, f"upload_status={upload_resp.status_code}, attachment_id={attachment_id}")
            else:
                step1 = StepResult(False, f"upload_status={upload_resp.status_code}, no attachment_ids")
        else:
            step1 = StepResult(False, f"upload_failed status={upload_resp.status_code} body={upload_resp.text[:240]}")
    else:
        step1 = StepResult(False, f"thread_create_failed status={create_resp.status_code} body={create_resp.text[:240]}")

    # Step 2: ask question about it
    step2 = StepResult(False, "not_run")
    question = "What is the approved budget from the uploaded PDF?"
    if thread_id and attachment_id:
        chat_resp = _post_json(
            f"{BASE_URL}/api/threads/{thread_id}/messages?token={TOKEN}",
            {"message": question, "attachment_ids": [attachment_id]},
        )
        if chat_resp.ok:
            step2 = StepResult(True, f"chat_status={chat_resp.status_code}")
        else:
            step2 = StepResult(False, f"chat_failed status={chat_resp.status_code} body={chat_resp.text[:240]}")

    # Step 3 and 4: fetch thread, then fetch again as refresh-equivalent
    step3 = StepResult(False, "not_run")
    step4 = StepResult(False, "not_run")
    first_get_data: dict[str, Any] | None = None
    second_get_data: dict[str, Any] | None = None
    if thread_id:
        first_get = requests.get(f"{BASE_URL}/api/threads/{thread_id}?token={TOKEN}", timeout=TIMEOUT)
        if first_get.ok:
            first_get_data = first_get.json()
        second_get = requests.get(f"{BASE_URL}/api/threads/{thread_id}?token={TOKEN}", timeout=TIMEOUT)
        if second_get.ok:
            second_get_data = second_get.json()

        if not first_get.ok:
            step3 = StepResult(False, f"first_get_failed status={first_get.status_code} body={first_get.text[:240]}")
            step4 = StepResult(False, f"refresh_get_failed status={second_get.status_code} body={second_get.text[:240]}")
        else:
            assistant = _extract_latest_message(first_get_data.get("messages", []), "assistant")
            assistant_text = (assistant or {}).get("content", "")
            uses_pdf_value = "42000" in assistant_text or "42,000" in assistant_text
            step3 = StepResult(
                uses_pdf_value,
                f"assistant_excerpt={assistant_text[:220]!r}",
            )

            if second_get.ok:
                user_msg = _extract_latest_message(second_get_data.get("messages", []), "user")
                attachment_ids = (user_msg or {}).get("attachment_ids") or []
                persisted = attachment_id in attachment_ids if attachment_id else False
                step4 = StepResult(
                    persisted,
                    f"refresh_status={second_get.status_code}, user_attachment_ids={attachment_ids}",
                )
            else:
                step4 = StepResult(False, f"refresh_get_failed status={second_get.status_code} body={second_get.text[:240]}")

    # Step 5: DB row proof
    step5 = StepResult(False, "not_run")
    database_url = (os.getenv("DATABASE_POOLER_URL") or os.getenv("DATABASE_URL") or "").replace("+asyncpg", "")
    if thread_id and database_url:
        try:
            with psycopg.connect(database_url, connect_timeout=15) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select id, thread_id, original_filename, mime_type, file_size
                        from chat_attachments
                        where thread_id = %s
                        order by created_at desc
                        limit 1
                        """,
                        (thread_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        step5 = StepResult(True, f"row={row}")
                    else:
                        step5 = StepResult(False, "no chat_attachments row found")
        except Exception as exc:
            step5 = StepResult(False, f"db_query_failed={type(exc).__name__}: {exc}")

    return ChecklistReport(
        step1_upload_pdf=step1,
        step2_ask_question=step2,
        step3_verify_response_uses_pdf=step3,
        step4_refresh_and_verify_persistence=step4,
        step5_db_row_proof=step5,
        thread_id=thread_id,
        attachment_id=attachment_id,
    )


if __name__ == "__main__":
    report = run()
    print(json.dumps(asdict(report), indent=2, default=str))
