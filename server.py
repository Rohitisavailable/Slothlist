"""Loopback-only web server and Backboard API bridge for Slothlist."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import urllib.error
import urllib.request

ROOT = Path(__file__).parent


def load_dotenv(path):
    """Load simple KEY=VALUE entries without overriding existing environment values."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if value.startswith(("'", '"')) and value.endswith(value[0]) and len(value) >= 2:
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


load_dotenv(ROOT / ".env")

HOST = "127.0.0.1"
PORT = 8765
PORT = int(os.environ.get("SLOTHLIST_PORT", PORT))
BACKBOARD_URL = "https://app.backboard.io/api/threads/messages"
BACKBOARD_API_KEY = os.environ.get("BACKBOARD_API_KEY", "")
MODEL_PROVIDER = os.environ.get("BACKBOARD_LLM_PROVIDER", "openrouter")
MODEL_NAME = os.environ.get("BACKBOARD_MODEL_NAME", "qwen/qwen-2.5-7b-instruct:free")
SYSTEM_PROMPT = (
    "You are Slothlist, a kind and practical task planner. Respect the user's energy and time. "
    "Do not invent deadlines or facts. Return a compact JSON object only with keys: headline (string), "
    "first_step (string), actions (array of objects with title and why strings, maximum 3), later (array of strings), "
    "delegate (array of strings), gentle_note (string). Suggest delegation only when reasonable. "
    "When memory is enabled, only retain durable planning preferences the user explicitly states; do not retain task items, names, or sensitive details."
)


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {
                "backboard": bool(BACKBOARD_API_KEY),
                "provider": MODEL_PROVIDER,
                "model": MODEL_NAME,
                "memory_default": "off",
            })
            return

        relative = "index.html" if self.path == "/" else self.path.lstrip("/")
        target = (ROOT / relative).resolve()
        if ROOT.resolve() not in target.parents or not target.is_file():
            self.send_error(404)
            return
        content_type = "text/css" if target.suffix == ".css" else "application/javascript" if target.suffix == ".js" else "text/html; charset=utf-8"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/plan":
            self.send_error(404)
            return
        if not BACKBOARD_API_KEY:
            return self._json(503, {"error": "Backboard is not configured yet. Set BACKBOARD_API_KEY in this PowerShell session and restart server.py."})
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            tasks = str(data.get("tasks", "")).strip()[:6000]
            energy = max(1, min(5, int(data.get("energy", 3))))
            minutes = max(5, min(180, int(data.get("minutes", 30))))
            if not tasks:
                return self._json(400, {"error": "Add a few tasks first."})

            assistant_id = str(data.get("assistant_id", ""))[:100]
            if assistant_id and not re.fullmatch(r"[A-Za-z0-9_-]+", assistant_id):
                return self._json(400, {"error": "The saved Backboard assistant ID is invalid. Clear this site's local storage and try again."})

            content = (
                f"Available energy: {energy}/5. Time budget: {minutes} minutes.\n"
                "Create today's gentle plan from this task dump:\n" + tasks
            )
            payload = {
                "content": content,
                "system_prompt": SYSTEM_PROMPT,
                "llm_provider": MODEL_PROVIDER,
                "model_name": MODEL_NAME,
                "json_output": True,
                "memory": "Auto" if data.get("remember_preferences") is True else "off",
                "stream": False,
            }
            if assistant_id:
                # No thread_id: each plan gets its own hosted thread under this assistant.
                payload["assistant_id"] = assistant_id

            request = urllib.request.Request(
                BACKBOARD_URL,
                data=json.dumps(payload).encode(),
                headers={"X-API-Key": BACKBOARD_API_KEY, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)

            raw_content = result.get("content") or "{}"
            try:
                plan = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError):
                # Some providers wrap structured output despite json_output=true.
                cleaned = str(raw_content).strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
                plan = json.loads(cleaned)
            if not isinstance(plan, dict):
                raise ValueError("The model response was not a JSON object")
            plan["assistant_id"] = result.get("assistant_id") or assistant_id or None
            plan["model_provider"] = result.get("model_provider") or MODEL_PROVIDER
            plan["model_name"] = result.get("model_name") or MODEL_NAME
            self._json(200, plan)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                message = "Backboard rejected the API key. Check BACKBOARD_API_KEY and restart the server."
            else:
                message = f"Backboard could not complete the plan (HTTP {exc.code}). Check the model settings and your Backboard account."
            self._json(502, {"error": message})
        except urllib.error.URLError:
            self._json(503, {"error": "Could not reach Backboard. Check your internet connection and try again."})
        except (ValueError, TypeError, json.JSONDecodeError):
            self._json(502, {"error": "Backboard returned an unreadable plan. Try again or choose another model."})
        except TimeoutError:
            self._json(504, {"error": "That took too long. Try again in a moment."})

    def log_message(self, fmt, *args):
        print("[slothlist] " + fmt % args)


if __name__ == "__main__":
    print(f"Slothlist is ready at http://{HOST}:{PORT}")
    if BACKBOARD_API_KEY:
        print(f"Backboard model: {MODEL_PROVIDER}/{MODEL_NAME}")
    else:
        print("Backboard API key is not set. Follow README setup, then restart this server.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
