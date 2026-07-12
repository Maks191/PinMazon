from __future__ import annotations

import secrets
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# Make the sibling ``pinmazon`` package importable when this file is launched
# exactly as documented: python scripts\pinterest_oauth.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pinmazon.settings import Settings
from pinmazon.token_store import PinterestTokenStore


settings = Settings()
state = secrets.token_urlsafe(24)
result: dict[str, str] = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != urlparse(settings.pinterest_redirect_uri).path:
            self.send_response(404)
            self.end_headers()
            return

        query = parse_qs(parsed.query)
        result["code"] = query.get("code", [""])[0]
        result["state"] = query.get("state", [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<h2>Pinterest connected. You can close this window.</h2>".encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def main():
    if not settings.pinterest_app_id or not settings.pinterest_app_secret:
        raise SystemExit("Add PINTEREST_APP_ID and PINTEREST_APP_SECRET to .env first.")

    redirect = urlparse(settings.pinterest_redirect_uri)
    host = redirect.hostname or "localhost"
    port = redirect.port or 8787
    server = HTTPServer((host, port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    params = {
        "client_id": settings.pinterest_app_id,
        "redirect_uri": settings.pinterest_redirect_uri,
        "response_type": "code",
        "scope": "boards:read,pins:read,pins:write",
        "state": state,
    }
    auth_url = "https://www.pinterest.com/oauth/?" + urlencode(params)
    print("Opening Pinterest authorization page...")
    print(auth_url)
    webbrowser.open(auth_url)

    deadline = time.time() + 180
    while "code" not in result and time.time() < deadline:
        time.sleep(0.25)

    if not result.get("code"):
        raise SystemExit("OAuth timed out.")
    if result.get("state") != state:
        raise SystemExit("OAuth state mismatch.")

    response = requests.post(
        "https://api.pinterest.com/v5/oauth/token",
        auth=(settings.pinterest_app_id, settings.pinterest_app_secret),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "code": result["code"],
            "redirect_uri": settings.pinterest_redirect_uri,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()
    PinterestTokenStore(settings).save(token)
    print(f"Saved token to {settings.token_path}")


if __name__ == "__main__":
    main()
