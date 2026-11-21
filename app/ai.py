import json
import urllib.error
import urllib.request

from flask import current_app


class AIError(Exception):
    """Raised when the AI service is not configured or cannot be reached."""


def ask_llm(prompt):
    provider = current_app.config.get("AI_PROVIDER", "").lower()
    if provider == "gemini":
        return ask_gemini(prompt)
    if provider == "ollama":
        return ask_ollama(prompt)
    raise AIError("AI is not configured. Set AI_PROVIDER to 'gemini' or 'ollama'.")


def post_json(url, payload, headers=None, timeout=30):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AIError(f"Could not reach the AI service: {error}") from error


def ask_gemini(prompt):
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise AIError("GEMINI_API_KEY is not set.")

    model = current_app.config["GEMINI_MODEL"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0},
    }
    data = post_json(url, payload, headers={"x-goog-api-key": api_key}, timeout=90)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIError("The AI service returned an unexpected response.") from error


def ask_ollama(prompt):
    url = current_app.config["OLLAMA_URL"].rstrip("/") + "/api/generate"
    payload = {
        "model": current_app.config["OLLAMA_MODEL"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }
    data = post_json(url, payload, timeout=120)
    try:
        return data["response"]
    except (KeyError, TypeError) as error:
        raise AIError("The AI service returned an unexpected response.") from error