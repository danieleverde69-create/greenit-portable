#!/usr/bin/env python3
"""Servizio locale per Green IT.

Espone API HTTP esclusivamente su 127.0.0.1. I segreti non vengono mai
memorizzati in chiaro: la chiave resta soltanto in memoria durante una sessione
sbloccata ed è derivata dalla master password.
"""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import re
import threading
import time
from pathlib import Path
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

APP_DIR = Path(os.environ.get("GREENIT_DATA_DIR", os.environ.get("GUARDIAIT_DATA_DIR", Path.cwd() / "data")))
DB_PATH = APP_DIR / "greenit.db"
BACKUP_DIR = APP_DIR / "backups"
OBSIDIAN_DIR = APP_DIR / "obsidian"
ITERATIONS = 600_000
SESSION_CIPHER: Fernet | None = None
LAST_SCHEDULED_BACKUP = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialise() -> None:
    with connect() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS companies (
              id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
              city TEXT NOT NULL DEFAULT '', contact TEXT NOT NULL DEFAULT '',
              email TEXT NOT NULL DEFAULT '', archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS credentials (
              id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
              title TEXT NOT NULL, username TEXT NOT NULL, category TEXT NOT NULL,
              secret BLOB NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(company_id) REFERENCES companies(id)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
              id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL,
              subject TEXT, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tickets (
              id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
              title TEXT NOT NULL, priority TEXT NOT NULL DEFAULT 'Media',
              status TEXT NOT NULL DEFAULT 'Aperto', due_date TEXT NOT NULL DEFAULT '',
              notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(company_id) REFERENCES companies(id)
            );
            CREATE TABLE IF NOT EXISTS deadlines (
              id INTEGER PRIMARY KEY AUTOINCREMENT, company_id INTEGER,
              title TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Licenza',
              due_date TEXT NOT NULL, supplier TEXT NOT NULL DEFAULT '',
              cost TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
              FOREIGN KEY(company_id) REFERENCES companies(id)
            );
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(companies)")}
        for column in ("city", "contact", "email"):
            if column not in columns:
                conn.execute(f"ALTER TABLE companies ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")


def setting(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def derive(password: str, salt: bytes) -> Fernet:
    raw = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(password.encode())
    return Fernet(base64.urlsafe_b64encode(raw))


def audit(event: str, subject: str = "") -> None:
    with connect() as conn:
        conn.execute("INSERT INTO audit_log(event, subject, created_at) VALUES(?,?,?)", (event, subject, utc_now()))


def backup_records() -> list[dict[str, Any]]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(BACKUP_DIR.glob("*.greenit-backup"), key=lambda item: item.stat().st_mtime, reverse=True)
    return [{"name": item.name, "size": item.stat().st_size, "created_at": datetime.fromtimestamp(item.stat().st_mtime, timezone.utc).isoformat()} for item in files]


def create_backup() -> dict[str, Any]:
    if SESSION_CIPHER is None:
        raise RuntimeError("Archivio bloccato")
    # Il database viene cifrato prima di lasciare l'archivio applicativo.
    with connect() as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    payload = SESSION_CIPHER.encrypt(DB_PATH.read_bytes())
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target = BACKUP_DIR / f"greenit_{stamp}.greenit-backup"
    target.write_bytes(payload)
    for old in sorted(BACKUP_DIR.glob("*.greenit-backup"), key=lambda item: item.stat().st_mtime, reverse=True)[7:]:
        old.unlink()
    return {"name": target.name, "size": target.stat().st_size, "created_at": utc_now()}


def scheduled_backup_loop() -> None:
    global LAST_SCHEDULED_BACKUP
    while True:
        now = datetime.now()
        marker = now.strftime("%Y-%m-%d")
        if now.weekday() < 5 and now.hour == 21 and now.minute == 30 and LAST_SCHEDULED_BACKUP != marker:
            try:
                record = create_backup()
                audit("backup_scheduled", record["name"])
            except RuntimeError:
                pass
            LAST_SCHEDULED_BACKUP = marker
        time.sleep(20)


def catch_up_backup() -> None:
    now = datetime.now()
    if now.weekday() >= 5 or now.hour < 21 or (now.hour == 21 and now.minute < 30):
        return
    today = now.strftime("%Y-%m-%d")
    if any(item["created_at"].startswith(today) for item in backup_records()):
        return
    try:
        record = create_backup()
        audit("backup_catch_up", record["name"])
    except RuntimeError:
        return


def safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9àèéìòùÀÈÉÌÒÙ _-]", "", value).strip()[:80] or "procedura"


class Handler(BaseHTTPRequestHandler):
    server_version = "GreenIT/0.1"

    def log_message(self, *_: Any) -> None:
        # Non registrare mai URL, payload o segreti nel log del servizio.
        return

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def payload(self) -> dict[str, Any]:
        size = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(size) or b"{}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            with connect() as conn:
                configured = setting(conn, "salt") is not None
            self.send_json({"status": "ok", "configured": configured, "locked": SESSION_CIPHER is None, "database": str(DB_PATH)})
            return
        if self.path == "/companies":
            with connect() as conn:
                rows = conn.execute("SELECT id,name,city,contact,email,archived,created_at FROM companies ORDER BY name").fetchall()
            self.send_json([dict(row) for row in rows])
            return
        if self.path == "/credentials":
            with connect() as conn:
                rows = conn.execute("""SELECT c.id,c.title,c.username,c.category,c.company_id,
                       co.name AS company,c.updated_at FROM credentials c
                       LEFT JOIN companies co ON co.id=c.company_id ORDER BY c.updated_at DESC""").fetchall()
            self.send_json([dict(row) for row in rows])
            return
        if self.path == "/tickets":
            with connect() as conn:
                rows = conn.execute("SELECT t.*,co.name AS company FROM tickets t LEFT JOIN companies co ON co.id=t.company_id ORDER BY t.updated_at DESC").fetchall()
            self.send_json([dict(row) for row in rows])
            return
        if self.path == "/deadlines":
            with connect() as conn:
                rows = conn.execute("SELECT d.*,co.name AS company FROM deadlines d LEFT JOIN companies co ON co.id=d.company_id WHERE d.active=1 ORDER BY d.due_date ASC").fetchall()
            self.send_json([dict(row) for row in rows])
            return
        if self.path == "/backup/status":
            records = backup_records()
            self.send_json({"destination": str(BACKUP_DIR), "retention": 7, "backups": records})
            return
        if self.path == "/audit":
            with connect() as conn:
                rows = conn.execute("SELECT id,event,subject,created_at FROM audit_log ORDER BY id DESC LIMIT 100").fetchall()
            self.send_json([dict(row) for row in rows])
            return
        if self.path == "/procedures":
            records = []
            if OBSIDIAN_DIR.exists():
                for path in OBSIDIAN_DIR.glob("*/**/*.md"):
                    records.append({"name": path.stem, "company_id": path.parent.parent.name, "path": str(path.relative_to(OBSIDIAN_DIR)), "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()})
            self.send_json(sorted(records, key=lambda item: item["updated_at"], reverse=True))
            return
        self.send_json({"error": "Risorsa non trovata"}, 404)

    def do_POST(self) -> None:
        global SESSION_CIPHER
        try:
            data = self.payload()
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "JSON non valido"}, 400)
            return
        if self.path == "/setup":
            password = data.get("master_password", "")
            if len(password) < 14:
                self.send_json({"error": "La master password deve avere almeno 14 caratteri"}, 400); return
            with connect() as conn:
                if setting(conn, "salt"):
                    self.send_json({"error": "Archivio già configurato"}, 409); return
                salt = os.urandom(16); cipher = derive(password, salt)
                conn.execute("INSERT INTO settings(key,value) VALUES(?,?)", ("salt", base64.b64encode(salt).decode()))
                conn.execute("INSERT INTO settings(key,value) VALUES(?,?)", ("verifier", cipher.encrypt(b"Green IT verifier").decode()))
            SESSION_CIPHER = cipher; audit("setup"); self.send_json({"configured": True}, 201); return
        if self.path == "/unlock":
            password = data.get("master_password", "")
            with connect() as conn:
                salt_text, verifier = setting(conn, "salt"), setting(conn, "verifier")
            if not salt_text or not verifier:
                self.send_json({"error": "Archivio non configurato"}, 409); return
            try:
                cipher = derive(password, base64.b64decode(salt_text)); cipher.decrypt(verifier.encode())
            except (InvalidToken, ValueError):
                audit("unlock_failed"); self.send_json({"error": "Master password non valida"}, 401); return
            SESSION_CIPHER = cipher; audit("unlock"); catch_up_backup(); self.send_json({"unlocked": True}); return
        if self.path == "/lock":
            SESSION_CIPHER = None; audit("lock"); self.send_json({"locked": True}); return
        if self.path.startswith("/credentials/") and self.path.endswith("/reveal"):
            if SESSION_CIPHER is None:
                self.send_json({"error": "Archivio bloccato"}, 423); return
            try:
                credential_id = int(self.path.split("/")[2])
                with connect() as conn:
                    row = conn.execute("SELECT secret FROM credentials WHERE id=?", (credential_id,)).fetchone()
                if not row: self.send_json({"error": "Credenziale non trovata"}, 404); return
                secret = SESSION_CIPHER.decrypt(row["secret"]).decode()
            except (ValueError, InvalidToken):
                self.send_json({"error": "Impossibile leggere il segreto"}, 400); return
            audit("credential_revealed", str(credential_id)); self.send_json({"password": secret}); return
        if self.path == "/companies":
            name = str(data.get("name", "")).strip()
            if not name: self.send_json({"error": "Nome azienda obbligatorio"}, 400); return
            with connect() as conn:
                cur = conn.execute("INSERT INTO companies(name,city,contact,email,created_at) VALUES(?,?,?,?,?)", (name, str(data.get("city", "")).strip(), str(data.get("contact", "")).strip(), str(data.get("email", "")).strip(), utc_now()))
            audit("company_created", name); self.send_json({"id": cur.lastrowid, "name": name, "city": data.get("city", ""), "contact": data.get("contact", ""), "email": data.get("email", "")}, 201); return
        if self.path == "/credentials":
            if SESSION_CIPHER is None:
                self.send_json({"error": "Archivio bloccato"}, 423); return
            required = ["title", "username", "password", "category"]
            if any(not str(data.get(key, "")).strip() for key in required):
                self.send_json({"error": "Campi obbligatori mancanti"}, 400); return
            now = utc_now()
            encrypted = SESSION_CIPHER.encrypt(str(data["password"]).encode())
            with connect() as conn:
                cur = conn.execute("INSERT INTO credentials(company_id,title,username,category,secret,created_at,updated_at) VALUES(?,?,?,?,?,?,?)", (data.get("company_id"), data["title"], data["username"], data["category"], encrypted, now, now))
            audit("credential_created", str(cur.lastrowid)); self.send_json({"id": cur.lastrowid}, 201); return
        if self.path == "/tickets":
            title = str(data.get("title", "")).strip()
            if not title: self.send_json({"error": "Titolo ticket obbligatorio"}, 400); return
            now = utc_now()
            with connect() as conn:
                cur = conn.execute("INSERT INTO tickets(company_id,title,priority,status,due_date,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (data.get("company_id"),title,data.get("priority","Media"),data.get("status","Aperto"),data.get("due_date",""),data.get("notes",""),now,now))
            audit("ticket_created", str(cur.lastrowid)); self.send_json({"id":cur.lastrowid},201); return
        if self.path == "/deadlines":
            title, due_date = str(data.get("title", "")).strip(), str(data.get("due_date", "")).strip()
            if not title or not due_date:
                self.send_json({"error": "Titolo e data di scadenza sono obbligatori"}, 400); return
            with connect() as conn:
                cur = conn.execute("INSERT INTO deadlines(company_id,title,category,due_date,supplier,cost,notes,created_at) VALUES(?,?,?,?,?,?,?,?)", (data.get("company_id"), title, data.get("category", "Licenza"), due_date, str(data.get("supplier", "")), str(data.get("cost", "")), str(data.get("notes", "")), utc_now()))
            audit("deadline_created", str(cur.lastrowid)); self.send_json({"id": cur.lastrowid}, 201); return
        if self.path == "/backup/run":
            try:
                record = create_backup()
            except RuntimeError as exc:
                self.send_json({"error": str(exc)}, 423); return
            audit("backup_created", record["name"]); self.send_json(record, 201); return
        if self.path == "/procedures":
            title, content = str(data.get("title", "")).strip(), str(data.get("content", ""))
            company_id = str(data.get("company_id", "")).strip()
            if not title or not company_id.isdigit():
                self.send_json({"error": "Titolo e azienda sono obbligatori"}, 400); return
            with connect() as conn:
                if not conn.execute("SELECT id FROM companies WHERE id=?", (int(company_id),)).fetchone():
                    self.send_json({"error": "Azienda non trovata"}, 404); return
            folder = OBSIDIAN_DIR / company_id; folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{safe_filename(title)}.md"; path.write_text(f"# {title}\n\n{content}\n", encoding="utf-8")
            audit("procedure_created", f"{company_id}:{title}"); self.send_json({"name": path.stem, "company_id": company_id, "path": str(path.relative_to(OBSIDIAN_DIR))}, 201); return
        self.send_json({"error": "Risorsa non trovata"}, 404)


if __name__ == "__main__":
    initialise()
    threading.Thread(target=scheduled_backup_loop, daemon=True).start()
    print(f"Green IT locale: http://127.0.0.1:8174 · dati: {DB_PATH}")
    ThreadingHTTPServer(("127.0.0.1", 8174), Handler).serve_forever()
