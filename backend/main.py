from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import os
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            phone TEXT,
            display_name TEXT NOT NULL,
            avatar_url TEXT,
            about TEXT DEFAULT 'Hey there! I am using Signal.',
            is_online INTEGER DEFAULT 1,
            last_seen TEXT,
            safety_number TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_user_id INTEGER NOT NULL,
            nickname TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, contact_user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT,
            avatar_url TEXT,
            disappearing_timer INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversation_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TEXT NOT NULL,
            UNIQUE(conversation_id, user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            message_type TEXT DEFAULT 'text',
            file_url TEXT,
            reply_to_id INTEGER,
            status TEXT DEFAULT 'sent',
            created_at TEXT NOT NULL,
            expires_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(message_id, user_id, emoji)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_or_create_user(conn, username: str) -> int:
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    if row:
        return row[0]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute("INSERT INTO users (username, display_name, created_at) VALUES (?, ?, ?)", (username, username.capitalize(), now))
    conn.commit()
    return c.lastrowid

def get_or_create_direct_conversation(conn, u1_id: int, u2_id: int) -> int:
    c = conn.cursor()
    c.execute('''
        SELECT c.id FROM conversations c
        JOIN conversation_members cm1 ON c.id = cm1.conversation_id
        JOIN conversation_members cm2 ON c.id = cm2.conversation_id
        WHERE c.type = 'direct' AND cm1.user_id = ? AND cm2.user_id = ?
    ''', (u1_id, u2_id))
    row = c.fetchone()
    if row:
        return row[0]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c.execute("INSERT INTO conversations (type, created_by, created_at) VALUES ('direct', ?, ?)", (u1_id, now))
    conv_id = c.lastrowid
    c.execute("INSERT INTO conversation_members (conversation_id, user_id, joined_at) VALUES (?, ?, ?)", (conv_id, u1_id, now))
    c.execute("INSERT INTO conversation_members (conversation_id, user_id, joined_at) VALUES (?, ?, ?)", (conv_id, u2_id, now))
    conn.commit()
    return conv_id

class Msg(BaseModel):
    sender: str
    receiver: str
    text: str

@app.get("/messages")
def get_all(sender: str, receiver: str):
    conn = get_db()
    u1_id = get_or_create_user(conn, sender)
    u2_id = get_or_create_user(conn, receiver)
    conv_id = get_or_create_direct_conversation(conn, u1_id, u2_id)
    
    c = conn.cursor()
    c.execute('''
        SELECT m.id, u.username, m.content
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.conversation_id = ?
        ORDER BY m.id ASC
    ''', (conv_id,))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "sender": r[1], "receiver": receiver if r[1] == sender else sender, "text": r[2]} for r in rows]

@app.post("/messages")
def post_msg(m: Msg):
    conn = get_db()
    u1_id = get_or_create_user(conn, m.sender)
    u2_id = get_or_create_user(conn, m.receiver)
    conv_id = get_or_create_direct_conversation(conn, u1_id, u2_id)
    
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (conversation_id, sender_id, content, created_at)
        VALUES (?, ?, ?, ?)
    ''', (conv_id, u1_id, m.text, now))
    conn.commit()
    conn.close()
    return {"status": "ok"}

active_sockets = []

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_sockets.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Broadcast raw text to all
            for s in active_sockets:
                try:
                    await s.send_text(data)
                except Exception:
                    pass
    except WebSocketDisconnect:
        if websocket in active_sockets:
            active_sockets.remove(websocket)

