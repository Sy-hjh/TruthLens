import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "runtime"
ROOT.mkdir(exist_ok=True)


@contextmanager
def connection():
    db = sqlite3.connect(ROOT / "cases.sqlite3")
    try:
        db.execute(
            "CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        with db:
            yield db
    finally:
        db.close()


def save(case):
    with connection() as db:
        db.execute(
            "INSERT INTO cases VALUES (?,?)",
            (case["id"], json.dumps(case, ensure_ascii=False)),
        )


def listing():
    with connection() as db:
        return [
            json.loads(row[0])
            for row in db.execute(
                "SELECT body FROM cases ORDER BY rowid DESC LIMIT 100"
            )
        ]


def get(case_id):
    with connection() as db:
        row = db.execute("SELECT body FROM cases WHERE id=?", (case_id,)).fetchone()
        return json.loads(row[0]) if row else None


def delete(case_id):
    with connection() as db:
        db.execute("DELETE FROM cases WHERE id=?", (case_id,))


def update(case):
    with connection() as db:
        return (
            db.execute(
                "UPDATE cases SET body=? WHERE id=?",
                (json.dumps(case, ensure_ascii=False), case["id"]),
            ).rowcount
            == 1
        )
