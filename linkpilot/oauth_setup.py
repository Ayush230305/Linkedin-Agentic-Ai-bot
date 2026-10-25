
import os
import secrets
import time
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv, set_key

# Always load the .env located beside this script.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI",
    "http://localhost:8000/callback",
).strip()

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPES = "openid profile w_member_social"

STATE = secrets.token_urlsafe(24)
RESULT = {}


def validate_config():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Missing LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET in .env"
        )

    placeholders = ("your_actual_", "replace_with_", "your_client_")
    if any(p in CLIENT_ID.lower() for p in placeholders):
        raise ValueError(
            "LINKEDIN_CLIENT_ID is still a placeholder. "
            "Copy the real Client ID from your LinkedIn app's Auth tab."
        )

    parsed = urlparse(REDIRECT_URI)

    if parsed.scheme != "http" or parsed.hostname not in (
        "localhost",
        "127.0.0.1",
    ):
        raise ValueError(
            "For this local script, REDIRECT_URI must use "
            "http://localhost:<port>/<path>."
        )

    if not parsed.port:
        raise ValueError("REDIRECT_URI must specify a port, e.g. :8000.")


_redirect = urlparse(REDIRECT_URI)
CALLBACK_PATH = _redirect.path or "/callback"
PORT = _redirect.port or 8000


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path != CALLBACK_PATH:
            self.send_error(404, "Unknown callback path")
            return

        query = parse_qs(parsed.query)

        if query.get("state", [""])[0] != STATE:
            RESULT["error"] = "OAuth state mismatch"
            self.send_error(400, "Invalid OAuth state")
            return

        if "error" in query:
            RESULT["error"] = query["error"][0]
            self.send_error(
                400,
                "LinkedIn authorization failed. Check the terminal.",
            )
            return

        code = query.get("code", [""])[0]
        if not code:
            RESULT["error"] = "LinkedIn did not return an authorization code"
            self.send_error(400, RESULT["error"])
            return

        RESULT["code"] = code

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"LinkedIn authorization received. Return to the terminal."
        )

    def log_message(self, *_):
        pass


def save_env(key, value):
    # Update only the specified key in the project's .env file.
    set_key(str(ENV_PATH), key, value, quote_mode="never")


def main():
    validate_config()

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": STATE,
        "scope": SCOPES,
    }
    auth_url = AUTH_URL + "?" + urlencode(params)

    try:
        server = HTTPServer(("localhost", PORT), CallbackHandler)
    except OSError as exc:
        raise RuntimeError(
            f"Could not start callback server on port {PORT}. "
            "Close the other process using this port or choose another port."
        ) from exc

    server.timeout = 1
    print("Opening LinkedIn authorization in your browser.")
    print("If it does not open automatically, copy the URL below:")
    print(auth_url)

    webbrowser.open(auth_url)

    deadline = time.time() + 300
    try:
        while not RESULT and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    if not RESULT.get("code"):
        raise RuntimeError(
            "OAuth authorization failed: "
            + RESULT.get("error", "Timed out after 5 minutes")
        )

    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": RESULT["code"],
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        token = token_data.get("access_token")

        if not token:
            raise RuntimeError("LinkedIn response did not contain an access token.")

        profile_response = requests.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

        if not profile_response.ok:
            raise RuntimeError(
                f"Could not read LinkedIn profile "
                f"(HTTP {profile_response.status_code}). "
                "Check that Sign In with LinkedIn using OpenID Connect "
                "is enabled for your app."
            )

        profile = profile_response.json()
        subject = profile.get("sub")

        if not subject:
            raise RuntimeError(
                "LinkedIn's userinfo response did not contain a 'sub' field."
            )

        member_urn = f"urn:li:person:{subject}"

        # Save credentials only after authorization and profile lookup succeed.
        save_env("LINKEDIN_ACCESS_TOKEN", token)
        save_env("LINKEDIN_MEMBER_URN", member_urn)

        print("OAuth successful.")
        print("Member URN:", member_urn)
        print("Access token saved to .env (not printed).")

    except requests.RequestException as exc:
        # Avoid printing headers or secrets in error messages.
        status = getattr(
            getattr(exc, "response", None), "status_code", None
        )
        if status:
            raise RuntimeError(
                f"LinkedIn OAuth request failed (HTTP {status}). "
                "Verify the Client ID, Client Secret, redirect URI, "
                "and app permissions."
            ) from None
        raise RuntimeError(
            "Could not connect to LinkedIn. Check your internet connection."
        ) from None


if __name__ == "__main__":
    main()
