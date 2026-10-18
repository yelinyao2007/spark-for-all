import json
import secrets
import sqlite3
import time
from pathlib import Path
from .models import SessionState

class Store:
    def __init__(self, path: str, ttl: int):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path, self.ttl = path, ttl
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, state TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS metrics(mode TEXT, name TEXT, value INTEGER NOT NULL, PRIMARY KEY(mode,name));
            ''')
    def connect(self):
        return sqlite3.connect(self.path)
    def purge(self):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
    def create(self, grade: int, mode: str):
        self.purge()
        sid = secrets.token_urlsafe(32)
        self.save(sid, SessionState(grade=grade))
        self.increment(mode, 'sessions')
        return sid
    def get(self, sid: str):
        self.purge()
        with self.connect() as db:
            row = db.execute('SELECT state FROM sessions WHERE id=?', (sid,)).fetchone()
        return SessionState.model_validate_json(row[0]) if row else None
    def save(self, sid: str, state: SessionState):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO sessions VALUES(?,?,?)',
                       (sid, state.model_dump_json(), time.time() + self.ttl))
    def delete(self, sid: str):
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE id=?', (sid,))
    def increment(self, mode: str, name: str, amount: int = 1):
        with self.connect() as db:
            db.execute('INSERT INTO metrics VALUES(?,?,?) ON CONFLICT(mode,name) DO UPDATE SET value=value+excluded.value', (mode,name,amount))
    def metrics(self, mode: str):
        with self.connect() as db:
            return dict(db.execute('SELECT name,value FROM metrics WHERE mode=?', (mode,)).fetchall())
