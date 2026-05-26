# 🤖 JARVIS: Unified Life Tracker API & Telegram Bot

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)

**JARVIS** is a modern, production-ready asynchronous personal life tracking assistant. It co-hosts a smart **Telegram Bot** alongside a high-performance **FastAPI REST API**, powered by OpenAI's `gpt-4o-mini` tool-calling engine. 

Instead of juggling separate bots or trackers, JARVIS gives you a **single, secure conversation window** on Telegram to track your financial expenses (in multiple currencies) and physical exercise workouts. It stores everything in a unified database and exposes clean REST endpoints to feed your personal web dashboard!

---

## 🌟 Key Features

*   **🎙️ The "JARVIS" Unified Assistant**: A single Telegram bot interface. Speak or type naturally—OpenAI dynamically parses and routes your messages to the correct database tables.
*   **💵 Multi-Currency Financial Logging**: Tracks transactions with native currency isolation (MXN, USD, EUR, etc.).
*   **🏃‍♂️ Athletic Workout Logging**: Keep tabs on your physical activities (Running, Weightlifting, Swimming, etc.) including duration, intensity, and detailed descriptions.
*   **📊 Web Dashboard Ready REST API**: Exposes endpoints (`/api/expenses`, `/api/workouts`, and `/api/summary`) with auto-generated Swagger interactive testing pages.
*   **🛡️ Fail-Secure Authorization**: Rigid numeric ID access check prevents unauthorized users from calling your bot or running up OpenAI API charges.
*   **🗜️ Auto Message-Chunking**: Splits large database outputs into sequential messages to guarantee the bot never crashes on Telegram's 4096-character API ceiling.
*   **🐳 Production-Ready Containerization**: Comes prepackaged with `Dockerfile` and `docker-compose.yml` for instant, isolated PostgreSQL deployments.
*   **🔌 Dual-Mode Storage Layer**: Uses PostgreSQL in production while maintaining a zero-configuration SQLite fallback (`life_tracker.db`) for immediate local development.

---

## 📐 Architecture Flow

```
   [ Telegram Client ]               [ Web Frontend Dashboard ]
            │                                     │
            ▼ (Updates/Commands)                  ▼ (JSON Requests)
    [ Asynchronous Bot ]                   [ FastAPI Endpoints ]
    (co-hosted in background task)      (/api/expenses, /api/workouts...)
            │                                     │
            ├───────────────► [ Database Layer ] ◄┘
            │               (Postgres / SQLite)
            ▼
    [ OpenAI Function API ]
      (GPT-4o-mini Router)
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

| Variable | Description |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | HTTP API token received from Telegram's BotFather. |
| `OPENAI_API_KEY` | Your secret OpenAI API developer key. |
| `ALLOWED_USER_ID` | Your numerical Telegram User ID (Fail-Secure; all other accounts will be blocked). |
| `DATABASE_URL` | *(Optional)* PostgreSQL connection string. Defaults to local SQLite if unset. |

---

## 🚀 Getting Started

### Option A: Local Run (SQLite Fallback)
1. **Initialize Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Launch Application**:
   ```bash
   python main.py
   ```
3. **Explore REST APIs**:
   Open your browser to: **`http://localhost:8000/docs`**

---

### Option B: Run in Production Mode (Docker + PostgreSQL)
Start a production-grade PostgreSQL stack alongside the web server and bot in one isolated step:
```bash
docker-compose up --build
```
*Docker will map named persistent storage to your host machine so data survives rebuilds.*

---

## 🤖 Interaction Examples

Talk to your bot on Telegram in Spanish or English:

*   **Track Expense**: *"Spent 115 mxn on a smoothie in lemo coffee paid with card"*
*   **Track USD Expense**: *"Compré una membresía de $5 dólares con transferencia"*
*   **Track Workout**: *"Did a heavy 45-minute weightlifting gym session"*
*   **Query Logs**: *"What did I spend and how did I exercise this week?"*
*   **Edit Expense**: *"Cambia el precio del smoothie de hoy a 120 pesos"*
*   **Delete Expense (Protected)**: *"Borra el gasto en lemo coffee"* -> *(JARVIS will ask for confirmation before calling delete).*

---

## 📝 License
Distributed under the MIT License. See `LICENSE` for more information.
