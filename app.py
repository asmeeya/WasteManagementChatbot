"""
EcoBot - Memory-Based Waste Management Chatbot
------------------------------------------------
Flask + Ollama (llama3.2:latest) chatbot that remembers past conversation
turns using a SQLite database (db.sqlite), and answers questions about
waste management (description, type, recycling details, recommendations,
and suggestions) grounded in data.json.

Prerequisites:
    1. Install Ollama:      https://ollama.com/download
    2. Pull the model:      ollama pull llama3.2:latest
    3. Make sure Ollama is running (ollama serve, if not already running)
    4. Install Python deps: pip install flask requests

Run:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime

import requests
from flask import Flask, render_template, request, jsonify, session, g

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite")
DATA_PATH = os.path.join(BASE_DIR, "data.json")

app = Flask(__name__, template_folder="templates")
app.secret_key = "ecobot-waste-management-secret-key"  # change in production

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:latest"

MAX_HISTORY_TURNS = 12  # number of past messages fed back to the model as memory


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def get_db():
    """Return a per-request SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the conversations table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_message(session_id, role, message):
    db = get_db()
    db.execute(
        "INSERT INTO conversations (session_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, message, datetime.utcnow().isoformat()),
    )
    db.commit()


def get_history(session_id, limit=MAX_HISTORY_TURNS):
    db = get_db()
    rows = db.execute(
        "SELECT role, message FROM conversations WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    # keep only the most recent `limit` messages for the model context
    trimmed = rows[-limit:] if len(rows) > limit else rows
    return [{"role": r["role"], "content": r["message"]} for r in trimmed]


def clear_history(session_id):
    db = get_db()
    db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    db.commit()


# ---------------------------------------------------------------------------
# Knowledge base + system prompt
# ---------------------------------------------------------------------------
def load_waste_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


WASTE_DATA = load_waste_data()


def build_system_prompt():
    return (
        "You are 'EcoBot', a friendly waste management assistant. "
        "You help users understand different types of waste, how to dispose "
        "of them, and how to recycle responsibly. For every relevant waste "
        "item mentioned, try to include: a short description, its type "
        "(biodegradable/non-biodegradable/hazardous/recyclable), recycling "
        "details, a recommendation for safe disposal, and a suggestion to "
        "reduce that kind of waste in future. Use the knowledge base JSON "
        "below as your primary source of truth. If something isn't covered "
        "in the knowledge base, answer using general best practices for "
        "sustainable waste management, and be clear that it's general "
        "guidance. Keep answers concise, practical, and easy to read, using "
        "short paragraphs or bullet points.\n\n"
        "WASTE MANAGEMENT KNOWLEDGE BASE (JSON):\n"
        f"{json.dumps(WASTE_DATA, indent=2)}"
    )


SYSTEM_PROMPT = build_system_prompt()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Render the main webpage with the floating chatbot icon."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")


@app.route("/api/history", methods=["GET"])
def history():
    """Return past conversation history so the chat window can restore memory."""
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"history": []})
    return jsonify({"history": get_history(session_id, limit=100)})


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle a user message: store it, call Ollama with memory context, store reply."""
    session_id = session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        session["session_id"] = session_id

    user_message = (request.json or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    save_message(session_id, "user", user_message)

    # Build the message list: system prompt + remembered history (includes the
    # message we just saved) so the bot has conversational memory.
    past_messages = get_history(session_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + past_messages

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
        reply = response.json().get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        reply = (
            "⚠️ I can't reach the Ollama server right now. Please make sure "
            "Ollama is running locally ('ollama serve') and that the "
            "'llama3.2:latest' model has been pulled."
        )
    except Exception as exc:  # noqa: BLE001
        reply = f"⚠️ Something went wrong while contacting the model: {exc}"

    save_message(session_id, "assistant", reply)

    return jsonify({"reply": reply})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Clear stored memory for the current session."""
    session_id = session.get("session_id")
    if session_id:
        clear_history(session_id)
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
