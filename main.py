import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from google import genai

load_dotenv()

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "你是使用者的 LINE 私人 AI 管家。請用繁體中文，簡潔、實用、可靠的方式回答。"
    "如果資訊不足就直接說明，避免瞎猜。",
)
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "./bot.db")
PORT = int(os.getenv("PORT", "8000"))

if not LINE_CHANNEL_SECRET:
    raise RuntimeError("Missing LINE_CHANNEL_SECRET")
if not LINE_CHANNEL_ACCESS_TOKEN:
    raise RuntimeError("Missing LINE_CHANNEL_ACCESS_TOKEN")
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY")

app = FastAPI(title="LINE Private AI Concierge (Gemini)")
client = genai.Client(api_key=GEMINI_API_KEY)


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )


def verify_signature(raw_body: bytes, x_line_signature: str) -> bool:
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).digest()
    computed_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed_signature, x_line_signature)


def save_message(user_id: str, role: str, content: str) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (user_id, role, content, int(time.time())),
        )


def clear_history(user_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))


def get_recent_history(user_id: str, max_turns: int = MAX_HISTORY_TURNS) -> List[Dict[str, str]]:
    limit = max_turns * 2
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def build_prompt(user_text: str, history: List[Dict[str, str]]) -> str:
    lines = [f"系統規則：{SYSTEM_PROMPT}", ""]
    if history:
        lines.append("以下是最近對話紀錄：")
        for item in history:
            speaker = "使用者" if item["role"] == "user" else "助理"
            lines.append(f"{speaker}：{item['content']}")
        lines.append("")
    lines.append(f"現在使用者說：{user_text}")
    lines.append("請直接回覆使用者。")
    return "\n".join(lines)


def generate_ai_reply(user_id: str, user_text: str) -> str:
    text = user_text.strip()

    if text.lower() in {"/help", "help"}:
        return (
            "可用指令：\n"
            "1. 直接聊天：例如『幫我整理今天待辦』\n"
            "2. /reset：清除這位使用者的對話記憶\n"
            "3. /help：顯示這份說明"
        )

    if text.lower() == "/reset":
        clear_history(user_id)
        return "已清除這個帳號的近期對話記憶。"

    history = get_recent_history(user_id)
    prompt = build_prompt(text, history)

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    output_text = getattr(response, "text", None)
    if not output_text:
        raise RuntimeError("Gemini returned empty text")

    reply_text = output_text.strip()
    save_message(user_id, "user", text)
    save_message(user_id, "assistant", reply_text)
    return reply_text


def reply_to_line(reply_token: str, text: str) -> None:
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": text[:5000],
            }
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=15)
    resp.raise_for_status()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "service": "line-private-ai-concierge-gemini"}


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: Optional[str] = Header(default=None)) -> JSONResponse:
    raw_body = await request.body()
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")

    if not verify_signature(raw_body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    body = json.loads(raw_body.decode("utf-8"))
    events = body.get("events", [])

    for event in events:
        if event.get("type") != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue

        reply_token = event.get("replyToken")
        user_id = event.get("source", {}).get("userId") or "anonymous"
        user_text = event.get("message", {}).get("text", "")

        try:
            reply_text = generate_ai_reply(user_id=user_id, user_text=user_text)
        except Exception as exc:
            reply_text = f"抱歉，我剛剛處理失敗了。請稍後再試一次。\n錯誤摘要：{str(exc)[:200]}"

        if reply_token:
            try:
                reply_to_line(reply_token, reply_text)
            except Exception as exc:
                print(f"Failed to reply to LINE: {exc}")

    return JSONResponse({"ok": True})
