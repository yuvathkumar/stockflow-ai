# StockFlow AI

![Tests](https://github.com/yuvathkumar/stockflow-ai/actions/workflows/tests.yml/badge.svg)

Inventory and order management web app that **predicts stockouts** and lets managers
**ask business questions in plain English**. Built with Python, Flask and SQL.

![Products page](docs/screenshots/products.png)

## Features

- **Products** – add, edit and archive products with server-side validation
- **Orders** – stock decreases automatically; orders are all-or-nothing
- **Audit log** – every stock change records who, when, before and after
- **Roles** – admins manage products; staff create orders and view stock
- **Reports** – stock value, revenue, top sellers and monthly sales (SQL aggregation)
- **CSV import/export** – row-level error messages, Excel-compatible
- **JSON API** – products, low-stock items and summary data
- **Stockout forecast** – days until stockout and suggested reorder quantities
- **Ask your data** – plain-English questions answered by AI-generated, safety-checked SQL

## Engineering highlights

| Problem | Solution |
|---|---|
| Two users ordering the last items at the same time | Atomic conditional `UPDATE ... WHERE quantity >= n` with row-count check |
| Partial orders leaving stock inconsistent | One database transaction per order, rollback on any failure |
| Untrusted SQL written by an AI | Validator + SQLite authorizer (table whitelist) + read-only connection + row limit |
| Stolen database exposing passwords | Passwords stored as salted scrypt hashes |
| Forged form submissions | CSRF tokens on every form |
| Login used to redirect users to fake sites | Only local redirect targets allowed |
| Excel formula injection in exports | Cells starting with `= + - @` are escaped |
| Slow pages from repeated queries | `selectinload` to avoid N+1 queries |
| Old orders changing when prices change | Unit price snapshotted on each order item |

## Tech stack

Python · Flask · SQLAlchemy · SQLite · Flask-Login · Flask-WTF · Jinja2 · Bootstrap 5 ·
pytest · Docker · Gunicorn · GitHub Actions · Google Gemini / Ollama

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

flask --app run init-db      # create database with sample data
flask --app run demo-sales   # optional: 45 days of order history for the forecast
python run.py                # open http://127.0.0.1:5000
```

Demo logins: `admin / admin123` (admin) · `staff / staff123` (staff)

### Enable "Ask your data" (optional)

Get a free API key from [Google AI Studio](https://aistudio.google.com), then set:

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key
```

Or run a local model with [Ollama](https://ollama.com) and set `AI_PROVIDER=ollama`.

## Run with Docker

```bash
docker build -t stockflow-ai .
docker run -p 8000:8000 -e SECRET_KEY=change-me -v stockflow-data:/app/instance stockflow-ai
```

Open http://localhost:8000. Health check: `/health`.

## Tests

```bash
python -m pytest -v
```

90+ tests cover validation, permissions, transactions, race-condition safety,
CSV edge cases, the forecast maths and AI-query security (including a simulated
prompt-injection attack). Tests run automatically on every push via GitHub Actions.

## Project structure

```
app/
├── __init__.py     app factory and configuration
├── models.py       database tables
├── auth.py         login, logout, role checks
├── routes.py       product pages
├── orders.py       order and stock-history pages
├── services.py     business logic (orders, imports, audit log)
├── reports.py      SQL reports
├── forecast.py     stockout prediction
├── ask.py          AI question → safe SQL
├── ai.py           Gemini / Ollama client
├── csv_io.py       CSV reading and writing
├── api.py          JSON API and health check
└── templates/      Jinja2 + Bootstrap pages
tests/              pytest suite
```

## Roadmap

- PostgreSQL with migrations (Alembic)
- Supplier management and purchase orders
- Seasonality-aware forecasting

---

Built by [Yuvathkumar Rayadurgam](https://linkedin.com/in/yuvathkumar)