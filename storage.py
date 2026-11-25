import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "documents.db"


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, filename TEXT NOT NULL, file_type TEXT NOT NULL,
            status TEXT NOT NULL, text TEXT NOT NULL, category TEXT, summary TEXT,
            keywords TEXT, entities TEXT, word_count INTEGER DEFAULT 0,
            uploaded_at TEXT NOT NULL, processed_at TEXT NOT NULL)""")


def save_document(filename, file_type, text, result):
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (doc_id, filename, file_type, "Processed", text, result["category"], result["summary"], json.dumps(result["keywords"]), json.dumps(result["entities"]), result["word_count"], now, now))
    return doc_id


def upload_document(filename, file_type, text):
    """Save an extracted document before the user requests NLP analysis."""
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (doc_id, filename, file_type, "Uploaded", text, None, None, "[]", "[]", len(text.split()), now, ""))
    return doc_id


def complete_document(doc_id, result):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as db:
        db.execute("""UPDATE documents SET status = 'Processed', category = ?, summary = ?,
            keywords = ?, entities = ?, word_count = ?, processed_at = ? WHERE id = ?""",
                   (result["category"], result["summary"], json.dumps(result["keywords"]),
                    json.dumps(result["entities"]), result["word_count"], now, doc_id))


def _decode(row):
    if row is None:
        return None
    d = dict(row)
    d["keywords"] = json.loads(d["keywords"] or "[]")
    d["entities"] = json.loads(d["entities"] or "[]")
    return d


def get_document(doc_id):
    with connect() as db:
        return _decode(db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())


def list_documents():
    with connect() as db:
        return [_decode(row) for row in db.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")]


def delete_document(doc_id):
    with connect() as db:
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
