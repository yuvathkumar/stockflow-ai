import re
import sqlite3

from sqlalchemy.exc import SQLAlchemyError

from . import db


class AskError(Exception):
    """Raised when a question cannot be answered safely."""


ALLOWED_TABLES = {"product", "orders", "order_items", "stock_movements"}
FORBIDDEN_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace"
    r"|vacuum|reindex|truncate|grant)\b",
    re.IGNORECASE,
)
MAX_ROWS = 100
MAX_QUESTION_LENGTH = 500

SCHEMA = """Tables (SQLite):
product(id, name, quantity, price, reorder_level, is_active)
orders(id, created_at, created_by_id)
order_items(id, order_id, product_id, quantity, unit_price)
stock_movements(id, product_id, order_id, change, quantity_before, quantity_after, reason, created_at)

Notes:
- Only include products where is_active = 1 unless the question asks about archived products.
- Revenue = order_items.quantity * order_items.unit_price.
- Dates are stored in UTC as text like '2026-11-22 10:30:00'. Use strftime('%Y-%m', created_at) for months.
- stock_movements.change is negative for stock going out (orders) and positive for stock coming in."""


def build_prompt(question):
    return (
        "You translate business questions into ONE SQLite SELECT query.\n\n"
        f"{SCHEMA}\n\n"
        "Rules:\n"
        "- Return only the SQL query. No explanation.\n"
        "- One SELECT statement only. Never modify data.\n"
        "- Use only the tables and columns listed above.\n\n"
        f"Question: {question}\n"
        "SQL:"
    )


def extract_sql(text):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.lower().startswith("sql"):
                text = text[3:]
    return text.strip().rstrip(";").strip()


def validate_sql(sql):
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise AskError("The AI did not return a query.")

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise AskError("Only SELECT queries are allowed.")
    if ";" in cleaned:
        raise AskError("Only one query is allowed.")
    if "--" in cleaned or "/*" in cleaned:
        raise AskError("Comments are not allowed in queries.")
    if FORBIDDEN_WORDS.search(cleaned):
        raise AskError("This query is not allowed.")
    return cleaned


def authorize(action, arg1, arg2, db_name, trigger):
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        return sqlite3.SQLITE_OK if arg1 in ALLOWED_TABLES else sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_DENY


def run_safe_query(sql):
    connection = db.session.connection()
    raw_connection = connection.connection.driver_connection

    connection.exec_driver_sql("PRAGMA query_only = ON")
    raw_connection.set_authorizer(authorize)
    try:
        result = connection.exec_driver_sql(f"SELECT * FROM ({sql}) LIMIT {MAX_ROWS}")
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]
    except SQLAlchemyError as error:
        raise AskError("This query is not allowed or could not run.") from error
    finally:
        raw_connection.set_authorizer(None)
        connection.exec_driver_sql("PRAGMA query_only = OFF")

    return columns, rows


def answer_question(question, llm):
    question = (question or "").strip()
    if not question:
        raise AskError("Type a question first.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise AskError(f"Questions must be {MAX_QUESTION_LENGTH} characters or fewer.")

    raw_answer = llm(build_prompt(question))
    sql = validate_sql(extract_sql(raw_answer))
    columns, rows = run_safe_query(sql)
    return {"sql": sql, "columns": columns, "rows": rows}