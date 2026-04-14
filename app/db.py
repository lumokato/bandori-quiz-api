import json
import os
from contextlib import contextmanager

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


pool: ConnectionPool | None = None


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL")
    return database_url


def get_pool() -> ConnectionPool:
    global pool
    if pool is None:
        pool = ConnectionPool(
            conninfo=get_database_url(),
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row},
            open=False,
        )
    return pool


def open_pool() -> None:
    get_pool().open()


def close_pool() -> None:
    current_pool = pool
    if current_pool is not None:
        current_pool.close()


@contextmanager
def get_conn():
    with get_pool().connection() as conn:
        yield conn


def check_database() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()


def ensure_schema() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_results (
                  id BIGSERIAL PRIMARY KEY,
                  attempt_id TEXT NOT NULL UNIQUE,
                  quiz_version TEXT NOT NULL,
                  total_questions INTEGER NOT NULL,
                  answers_json TEXT NOT NULL,
                  best_match_key TEXT,
                  best_match_name TEXT,
                  best_match_percentage DOUBLE PRECISION,
                  top_three_json TEXT NOT NULL,
                  scores_json TEXT NOT NULL,
                  country TEXT,
                  region TEXT,
                  region_code TEXT,
                  city TEXT,
                  page_path TEXT,
                  page_url TEXT,
                  user_agent TEXT,
                  created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS quiz_results_created_at_idx
                ON quiz_results (created_at DESC)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS quiz_results_best_match_idx
                ON quiz_results (best_match_key, best_match_name)
                """
            )
        conn.commit()


def insert_result(payload: dict, meta: dict) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO quiz_results (
                  attempt_id,
                  quiz_version,
                  total_questions,
                  answers_json,
                  best_match_key,
                  best_match_name,
                  best_match_percentage,
                  top_three_json,
                  scores_json,
                  country,
                  region,
                  region_code,
                  city,
                  page_path,
                  page_url,
                  user_agent,
                  created_at
                ) VALUES (
                  %(attempt_id)s,
                  %(quiz_version)s,
                  %(total_questions)s,
                  %(answers_json)s,
                  %(best_match_key)s,
                  %(best_match_name)s,
                  %(best_match_percentage)s,
                  %(top_three_json)s,
                  %(scores_json)s,
                  %(country)s,
                  %(region)s,
                  %(region_code)s,
                  %(city)s,
                  %(page_path)s,
                  %(page_url)s,
                  %(user_agent)s,
                  %(created_at)s
                )
                ON CONFLICT (attempt_id) DO NOTHING
                """,
                {**payload, **meta},
            )
        conn.commit()


def fetch_overview_stats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*)::BIGINT AS total FROM quiz_results")
            total = cur.fetchone()

            cur.execute("SELECT created_at FROM quiz_results ORDER BY id DESC LIMIT 1")
            latest = cur.fetchone()

            cur.execute(
                """
                SELECT
                  best_match_key,
                  best_match_name,
                  COUNT(*)::BIGINT AS count,
                  ROUND(AVG(best_match_percentage)::numeric, 2) AS avg_percentage
                FROM quiz_results
                WHERE best_match_key IS NOT NULL
                GROUP BY best_match_key, best_match_name
                ORDER BY count DESC, avg_percentage DESC
                LIMIT 20
                """
            )
            ranking = cur.fetchall()

    return {
        "ok": True,
        "total_results": int(total["total"] or 0),
        "latest_created_at": latest["created_at"] if latest else None,
        "top_best_matches": ranking,
    }


def fetch_question_stats() -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*)::BIGINT AS total_results, MAX(total_questions) AS total_questions
                FROM quiz_results
                """
            )
            meta = cur.fetchone()

            total_results = int(meta["total_results"] or 0)
            total_questions = int(meta["total_questions"] or 0)

            if not total_results or not total_questions:
                return {
                    "ok": True,
                    "total_results": 0,
                    "total_questions": total_questions,
                    "questions": [],
                }

            cur.execute("SELECT answers_json FROM quiz_results ORDER BY id DESC")
            rows = cur.fetchall()

    counters = [
        {
            "question_index": index,
            "counts": {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0},
            "total_answers": 0,
        }
        for index in range(total_questions)
    ]
    labels = ["A", "B", "C", "D", "E"]

    for row in rows:
        try:
            answers = json.loads(row["answers_json"])
        except (TypeError, json.JSONDecodeError):
            continue

        if not isinstance(answers, list):
            continue

        for index, value in enumerate(answers):
            if type(value) is not int or index >= len(counters):
                continue

            label = labels[value] if 0 <= value < len(labels) else None
            if label is None:
                continue

            counters[index]["counts"][label] += 1
            counters[index]["total_answers"] += 1

    return {
        "ok": True,
        "total_results": total_results,
        "total_questions": total_questions,
        "questions": counters,
    }
