"""Persistent research artifacts and human review."""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class IntelligenceStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS reviews (seq INTEGER PRIMARY KEY, run_id TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL, reviewed_at TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save_run(self, run: dict):
        if not re.fullmatch(r"[0-9a-f]{32}", run.get("id", "")):
            raise ValueError("Invalid research id")
        try:
            with self._connect() as db:
                db.execute("INSERT INTO runs VALUES (?, ?, ?)", (run["id"], run.get("created_at", ""), json.dumps(run, ensure_ascii=False)))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Research records are immutable") from exc

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            run = json.loads(row[0])
            review = db.execute("SELECT status, note, reviewed_at FROM reviews WHERE run_id = ? ORDER BY seq DESC LIMIT 1", (run_id,)).fetchone()
        if review:
            run["review"] = dict(zip(("status", "note", "reviewed_at"), review))
        # Editable English presentation is separate from immutable research evidence.
        if run.get("revision", {}).get("kind") == "ai_assisted_editorial":
            path = self.path.parent / "display-copies" / (run_id + ".en.json")
            try:
                display_copy = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(display_copy, dict):
                    run["display_copy"] = display_copy
            except (OSError, ValueError):
                pass
        return run

    def list_runs(self, limit: int = 50) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT id FROM runs ORDER BY rowid DESC LIMIT ?", (min(max(limit, 1), 100),)).fetchall()
        return [self.get_run(row[0]) for row in rows]

    def review_run(self, run_id: str, status: str, note: str):
        if status not in {"approved", "rejected", "pending"} or len(note) > 2000:
            raise ValueError("Choose approved, rejected or pending; keep notes under 2000 characters.")
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM runs WHERE id = ?", (run_id,)).fetchone():
                raise KeyError(run_id)
            db.execute("INSERT INTO reviews (run_id, status, note, reviewed_at) VALUES (?, ?, ?, ?)", (run_id, status, note.strip(), now))
