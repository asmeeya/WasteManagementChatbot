# ♻️ EcoBot – Memory-Based Waste Management Chatbot

EcoBot is a Flask web application with a floating chatbot widget that helps
users understand how to identify, dispose of, and recycle different types of
waste. It uses a local LLM ([Ollama](https://ollama.com) running
`llama3.2:latest`) grounded in a custom waste-management knowledge base, and
remembers the conversation using a SQLite database so context is preserved
across messages and page reloads.

---

## ✨ Features

- 💬 Floating chat icon at the **bottom-right** of the page — click to
  open/close the chat window
- 🧠 **Memory-based** conversations — chat history is stored in `db.sqlite`
  and reloaded automatically, even after refreshing the page
- ♻️ Knowledge base (`data.json`) covering 8 waste categories: Plastic,
  E-Waste, Organic, Paper/Cardboard, Glass, Metal, Hazardous, and Medical
  waste — each with a **description, type, recycling details,
  recommendation, and suggestion**
- 🎨 UI built entirely with **Bootstrap 5** (via CDN) — no custom CSS/JS files
- 🔄 "Reset" button to clear the current conversation's memory
- 🤖 Powered by a locally running **Ollama** model (`llama3.2:latest`)

---

## 📁 Project Structure

```
session3/
├── app.py               # Flask backend (routes, SQLite memory, Ollama calls)
├── data.json             # Waste management knowledge base
├── db.sqlite               # SQLite database (auto-created if missing)
└── templates/
    └── index.html               # Bootstrap-only webpage + chatbot widget
```

> ⚠️ **Folder name matters:** the folder must be named exactly `templates`
> (plural, lowercase) since `app.py` uses Flask's default template loader.
> If it's misspelled or renamed, you'll get a
> `jinja2.exceptions.TemplateNotFound: index.html` error.

---

## 🧰 Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.com/download) installed and running locally
- The `llama3.2:latest` model pulled in Ollama

---

## 🚀 Local Setup & Run

1. **Clone or download** this project into a folder named `session3`.

2. **Install Python dependencies:**
   ```bash
   pip install flask requests
   ```

3. **Install Ollama** (if not already installed):
   [https://ollama.com/download](https://ollama.com/download)

4. **Pull the model** (one-time download):
   ```bash
   ollama pull llama3.2:latest
   ```

5. **Start the Ollama server** (if it isn't already running in the background):
   ```bash
   ollama serve
   ```

6. **Run the Flask app:**
   ```bash
   python app.py
   ```

7. **Open the app** in your browser:
   ```
   http://127.0.0.1:5000
   ```

8. Click the 💬 icon in the bottom-right corner to start chatting with EcoBot.

---

## 🧠 How Memory Works

- Each visitor is assigned a `session_id` stored in a browser cookie.
- Every user message and bot reply is saved to the `conversations` table in
  `db.sqlite`.
- On each new message, the last 12 messages for that session are retrieved
  from SQLite and sent to the model as conversational context.
- Reopening the chat window calls `/api/history` to restore the full
  conversation from the database.
- Clicking **Reset** deletes that session's rows from `db.sqlite`.

**`conversations` table schema:**

| Column     | Type     | Description                        |
|------------|----------|-------------------------------------|
| id         | INTEGER  | Primary key, auto-increment         |
| session_id | TEXT     | Identifies a user's chat session    |
| role       | TEXT     | `user` or `assistant`               |
| message    | TEXT     | The message content                 |
| timestamp  | DATETIME | When the message was stored (UTC)   |

---

## 🔌 API Endpoints

| Method | Endpoint        | Description                                  |
|--------|-----------------|-----------------------------------------------|
| GET    | `/`             | Renders the main webpage with chatbot widget  |
| GET    | `/api/history`  | Returns the stored conversation for the session |
| POST   | `/api/chat`     | Sends a user message, returns EcoBot's reply  |
| POST   | `/api/reset`    | Clears the conversation memory for the session |

---

## ⚙️ Configuration

Environment variables (optional):

| Variable      | Default                              | Description                        |
|---------------|----------------------------------------|--------------------------------------|
| `OLLAMA_URL`  | `http://localhost:11434/api/chat`     | URL of the Ollama chat endpoint     |
| `OLLAMA_MODEL`| `llama3.2:latest`                     | Model name to use                   |

---

## 🐞 Troubleshooting

**`jinja2.exceptions.TemplateNotFound: index.html`**
- Make sure there's a folder named exactly `templates` (plural) directly
  inside `session3/`, sitting next to `app.py`.
- `index.html` must be directly inside that `templates` folder — not in a
  sub-folder, and not loose inside `session3/`.
- Restart the Flask server (`Ctrl+C`, then `python app.py` again) after
  fixing the folder/file — Flask won't pick up structural changes on its own.

**"Can't reach the Ollama server" in the chat reply**
- Ollama isn't running. Open a terminal and run `ollama serve`, and keep
  that window open while using the chatbot.
- Confirm the model is pulled: `ollama pull llama3.2:latest`.

**Port 5000 already in use**
- Stop the other process, or run this app on a different port by changing
  `app.run(debug=True, port=5000)` to another port number.

**Chat window doesn't remember previous messages**
- Check that `db.sqlite` exists in the same folder as `app.py`. If it was
  deleted, `app.py` recreates it automatically on the next run via `init_db()`.
- Make sure cookies aren't blocked in your browser — the `session_id` is
  stored in a cookie.

---

## ☁️ Deploying on Render

⚠️ **Important:** Render's web services cannot run Ollama or host a local
LLM — there's no way to install/run the Ollama daemon or the `llama3.2`
model on a standard Render web service (insufficient RAM/disk, no
persistent background process support on most plans).

To deploy the **Flask app** on Render, you have two options:

### Option A — Point Render at a remote Ollama instance
Run Ollama on your own machine or a separate VPS with GPU/RAM to spare,
expose it (e.g. via a reverse proxy or tunnel), and set the `OLLAMA_URL`
environment variable in Render to that public address.

### Option B — Swap Ollama for a hosted LLM API
Replace the Ollama call in `app.py` with a hosted API (e.g. Anthropic,
OpenAI, Groq) that doesn't require a locally running server.

**Render service settings (once the model backend is sorted):**

- **Build Command:**
  ```
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```
  gunicorn app:app
  ```
- **Environment Variables:**
  - `OLLAMA_URL` (if using Option A)
  - Any API keys (if using Option B)
  - `SECRET_KEY` for Flask sessions in production

Note: `db.sqlite` on Render's free/standard disk is **ephemeral** — it may
reset on redeploys. For persistent chat history in production, consider
Render's paid persistent disk add-on or an external database.

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLite
- **LLM:** Ollama (`llama3.2:latest`)
- **Frontend:** HTML + Bootstrap 5 (CDN only, no custom CSS/JS)

---

## 📄 License

This project is provided as-is for educational/demo purposes. Feel free to
modify and extend it.
