from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Callable, TypedDict
from uuid import uuid4

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("COMPASS_DATABASE_PATH", ROOT / "data" / "compass.sqlite3"))
CHECKPOINT_PATH = Path(os.getenv("COMPASS_CHECKPOINT_PATH", ROOT / "data" / "checkpoints.sqlite3"))
STATIC_DIR = Path(os.getenv("COMPASS_STATIC_DIR", ROOT / "frontend" / "dist"))
MAX_BODY_BYTES = 2 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_decisions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 1_000:
        raise ValueError("decisions must be a list with at most 1,000 records")
    for item in value:
        if not isinstance(item, dict) or not isinstance(item.get("id"), (int, float)):
            raise ValueError("each decision needs a numeric id")
        if not isinstance(item.get("title"), str) or not item["title"].strip():
            raise ValueError("each decision needs a title")
        if not isinstance(item.get("options"), list) or len(item["options"]) < 2:
            raise ValueError("each decision needs at least two options")
    return value


class WorkspaceInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    decisions: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("decisions")
    @classmethod
    def check_decisions(cls, value: Any) -> list[dict[str, Any]]:
        return validate_decisions(value)


class DecisionsInput(BaseModel):
    decisions: list[dict[str, Any]]

    @field_validator("decisions")
    @classmethod
    def check_decisions(cls, value: Any) -> list[dict[str, Any]]:
        return validate_decisions(value)


class AssistInput(BaseModel):
    decision_id: int | float


class AssessmentState(TypedDict, total=False):
    decision: dict[str, Any]
    deterministic: dict[str, Any]
    assessment: dict[str, Any]


def connect_database(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute(
        """CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            revision INTEGER NOT NULL DEFAULT 1,
            decisions TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    return connection


@contextmanager
def database():
    connection = connect_database()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def public_workspace(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "revision": row["revision"],
        "decisions": json.loads(row["decisions"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_workspace(payload: WorkspaceInput) -> tuple[dict[str, Any], str]:
    workspace_id = secrets.token_urlsafe(12)
    token = secrets.token_urlsafe(32)
    timestamp = utc_now()
    with database() as connection:
        connection.execute(
            "INSERT INTO workspaces VALUES (?, ?, ?, 1, ?, ?, ?)",
            (workspace_id, payload.name, token_hash(token), json.dumps(payload.decisions), timestamp, timestamp),
        )
        row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
    return public_workspace(row), token


def authorized_workspace(workspace_id: str, token: str) -> sqlite3.Row:
    with database() as connection:
        row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
    if row is None or not hmac.compare_digest(row["token_hash"], token_hash(token)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid workspace credentials")
    return row


def save_decisions(workspace_id: str, token: str, revision: int, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    authorized_workspace(workspace_id, token)
    timestamp = utc_now()
    with database() as connection:
        result = connection.execute(
            "UPDATE workspaces SET decisions = ?, revision = revision + 1, updated_at = ? WHERE id = ? AND revision = ?",
            (json.dumps(decisions), timestamp, workspace_id, revision),
        )
        if result.rowcount != 1:
            current = connection.execute("SELECT revision FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": "Workspace changed on another device", "revision": current["revision"]})
        row = connection.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,)).fetchone()
    return public_workspace(row)


def prepare_assessment(state: AssessmentState) -> AssessmentState:
    decision = state["decision"]
    criteria = decision.get("criteria", [])
    options = decision.get("options", [])
    total = len(criteria) * len(options)
    complete = sum(
        1 for option in options for criterion in criteria
        if option.get("scores", {}).get(criterion.get("id")) is not None
    )
    return {"deterministic": {
        "evaluation_progress": round(complete / total * 100) if total else 0,
        "option_count": len(options),
        "criterion_count": len(criteria),
        "evidence_count": len(decision.get("evidence", [])),
        "has_rationale": bool(decision.get("rationale", "").strip()),
    }}


def evaluate_with_jev(state: AssessmentState) -> AssessmentState:
    from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

    model = os.getenv("TYPESAFE_DEFAULT_MODEL", "jev-latest")
    questions = {
        "readiness": Score(
            instructions="How ready is this record for a human to make a well-supported decision? Judge completeness and evidence quality only. Do not choose an option.",
            criteria=["Not ready: essential context is missing", "Needs work: material gaps remain", "Ready: enough support for a human decision"],
        ),
        "focus": Choice(
            instructions="Which single area most needs the human reviewer's attention?",
            criteria={
                "evidence": "Evidence is missing, weak, or disconnected from scores.",
                "criteria": "Criteria or weights are unclear or misaligned.",
                "alternatives": "Options are incomplete or not comparable.",
                "rationale": "The recorded rationale is insufficient.",
                "ready": "No material gap is apparent.",
            },
        ),
        "unsupported": Noul(instructions="Does the record contain important scores or claims that lack supporting evidence?"),
    }
    context = json.dumps({"decision": state["decision"], "computed": state["deterministic"]}, ensure_ascii=True)
    with TypeSafeClient(model=model) as client:
        result = client.system_one(context, questions)
    readiness = result.scores["readiness"]
    focus = result.choices["focus"]
    unsupported = result.nouls["unsupported"]
    labels = ["not_ready", "needs_work", "ready"]
    level = labels[max(0, min(2, round(readiness.score)))]
    return {"assessment": {
        "readiness": level,
        "readiness_score": readiness.score,
        "confidence": readiness.confidence,
        "focus": focus.choice,
        "focus_confidence": focus.confidence,
        "unsupported_evidence_probability": unsupported.noul,
        "needs_attention": level != "ready" or readiness.confidence < 0.75 or focus.confidence < 0.65 or unsupported.noul > 0.65,
        "model": result.model,
        "request_id": result.request_id,
        "human_decision_required": True,
    }}


def build_assessment_graph(checkpointer: Any, evaluator: Callable[[AssessmentState], AssessmentState] = evaluate_with_jev):
    graph = StateGraph(AssessmentState)
    graph.add_node("prepare", prepare_assessment)
    graph.add_node("jev_review", evaluator)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "jev_review")
    graph.add_edge("jev_review", END)
    return graph.compile(checkpointer=checkpointer)


graph_lock = Lock()
assessment_graph: Any = None
checkpoint_connection: sqlite3.Connection | None = None


def get_assessment_graph():
    global assessment_graph, checkpoint_connection
    with graph_lock:
        if assessment_graph is None:
            CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_connection = sqlite3.connect(CHECKPOINT_PATH, check_same_thread=False)
            assessment_graph = build_assessment_graph(SqliteSaver(checkpoint_connection))
    return assessment_graph


app = FastAPI(title="Compass API", version="1.0.0")
origins = [origin.strip() for origin in os.getenv("COMPASS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type", "If-Match"])
security = HTTPBearer(auto_error=False)


@app.middleware("http")
async def security_and_size_headers(request: Request, call_next: Callable):
    length = request.headers.get("content-length")
    if length and int(length) > MAX_BODY_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request body exceeds 2 MB")
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def bearer(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return credentials.credentials


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "jev": "configured" if os.getenv("TYPESAFE_API_KEY") else "needs_api_key"}


@app.post("/api/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace_route(payload: WorkspaceInput) -> dict[str, Any]:
    workspace, token = create_workspace(payload)
    return {"workspace": workspace, "token": token}


@app.get("/api/workspaces/{workspace_id}")
def get_workspace_route(workspace_id: str, token: str = Depends(bearer)) -> dict[str, Any]:
    return {"workspace": public_workspace(authorized_workspace(workspace_id, token))}


@app.put("/api/workspaces/{workspace_id}/decisions")
def save_decisions_route(payload: DecisionsInput, workspace_id: str, if_match: int = Header(alias="If-Match"), token: str = Depends(bearer)) -> dict[str, Any]:
    return {"workspace": save_decisions(workspace_id, token, if_match, payload.decisions)}


@app.post("/api/workspaces/{workspace_id}/assist")
def assist_route(payload: AssistInput, workspace_id: str, token: str = Depends(bearer)) -> dict[str, Any]:
    if not os.getenv("TYPESAFE_API_KEY"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Set TYPESAFE_API_KEY to enable Jev review")
    workspace = public_workspace(authorized_workspace(workspace_id, token))
    decision = next((item for item in workspace["decisions"] if item.get("id") == payload.decision_id), None)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    run_id = str(uuid4())
    try:
        result = get_assessment_graph().invoke({"decision": decision}, {"configurable": {"thread_id": run_id}})
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Jev review failed") from error
    return {"run_id": run_id, "assessment": result["assessment"], "computed": result["deterministic"]}


if STATIC_DIR.is_dir():
    assets = STATIC_DIR / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        candidate = (STATIC_DIR / path).resolve()
        if candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
