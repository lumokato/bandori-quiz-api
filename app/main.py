import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import (
    check_database,
    close_pool,
    ensure_schema,
    fetch_overview_stats,
    fetch_question_stats,
    insert_result,
    open_pool,
)
from app.models import ResultPayload


def build_meta(request: Request, payload: ResultPayload) -> dict:
    return {
        "country": (request.headers.get("cf-ipcountry") or "")[:16] or None,
        "region": (payload.region or "")[:128] or None,
        "region_code": (payload.regionCode or "")[:32] or None,
        "city": (payload.city or "")[:128] or None,
        "page_path": payload.pagePath[:255],
        "page_url": payload.pageUrl[:2048],
        "user_agent": (payload.userAgent or request.headers.get("user-agent") or "")[:1024],
    }


def normalize_payload(payload: ResultPayload) -> dict:
    return {
        "attempt_id": payload.attemptId,
        "quiz_version": payload.quizVersion,
        "total_questions": payload.totalQuestions,
        "answers_json": json.dumps(payload.answers),
        "best_match_key": payload.bestMatch.key if payload.bestMatch else None,
        "best_match_name": payload.bestMatch.name if payload.bestMatch else None,
        "best_match_percentage": payload.bestMatch.percentage if payload.bestMatch else None,
        "top_three_json": json.dumps(payload.topThree[:3]),
        "scores_json": json.dumps(payload.scores),
        "created_at": payload.submittedAt,
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    open_pool()
    ensure_schema()
    yield
    close_pool()


app = FastAPI(title="bandori-quiz-api", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "https://example.com")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    return JSONResponse(
        status_code=400,
        content={"ok": False, "error": first_error.get("msg") or "Invalid request payload"},
    )


@app.get("/")
async def root():
    return {"ok": True, "service": "bandori-quiz-api"}


@app.get("/healthz")
async def healthz():
    try:
        check_database()
        return {"ok": True}
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(error) or "Database unavailable"},
        )


@app.post("/api/save-result")
async def save_result(payload: ResultPayload, request: Request):
    try:
        insert_result(normalize_payload(payload), build_meta(request, payload))
        return {"ok": True}
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(error) or "Failed to save result"},
        )


@app.get("/api/stats")
async def stats():
    try:
        return fetch_overview_stats()
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(error) or "Failed to load stats"},
        )


@app.get("/api/stats/questions")
async def question_stats():
    try:
        return fetch_question_stats()
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(error) or "Failed to load question stats"},
        )
