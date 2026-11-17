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


def initialize():
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in db.execute("PRAGMA table_info(cases)")}
        if "owner_id" not in columns:
            db.execute("ALTER TABLE cases ADD COLUMN owner_id INTEGER")
        if "created_at" not in columns:
            db.execute("ALTER TABLE cases ADD COLUMN created_at TEXT")
            db.execute("UPDATE cases SET created_at=json_extract(body,'$.created_at')")
        db.execute("CREATE INDEX IF NOT EXISTS cases_owner ON cases(owner_id)")
        db.execute("CREATE INDEX IF NOT EXISTS cases_created ON cases(created_at)")


def save(case, owner_id=None):
    with connection() as db:
        if owner_id is None and "owner_id" not in {row[1] for row in db.execute("PRAGMA table_info(cases)")}:
            db.execute("INSERT INTO cases(id,body) VALUES (?,?)", (case["id"], json.dumps(case, ensure_ascii=False)))
        else:
            db.execute("INSERT INTO cases(id,body,owner_id,created_at) VALUES (?,?,?,?)",
                       (case["id"], json.dumps(case, ensure_ascii=False), owner_id, case.get("created_at")))


def _load_report(report):
    from .report_summary import update_summary
    from .tamper import with_saved_regions

    return update_summary(with_saved_regions(report))


def listing(include_internal=False, *, owner_id=None):
    with connection() as db:
        query = "SELECT body FROM cases"
        args = ()
        if owner_id is not None:
            query += " WHERE owner_id=?"
            args = (owner_id,)
        rows = [
            json.loads(row[0])
            for row in db.execute(query + " ORDER BY rowid DESC LIMIT 100", args)
        ]
    return [_load_report(r) for r in rows if include_internal or not r.get('internal_only')]


def get(case_id):
    with connection() as db:
        row = db.execute("SELECT body FROM cases WHERE id=?", (case_id,)).fetchone()
    return _load_report(json.loads(row[0])) if row else None


def owned_by(case_id, account_id):
    with connection() as db:
        return bool(db.execute("SELECT 1 FROM cases WHERE id=? AND owner_id=?", (case_id, account_id)).fetchone())


def expired_reports(cutoff):
    with connection() as db:
        return [row[0] for row in db.execute("SELECT id FROM cases WHERE created_at<?", (cutoff,))]


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
