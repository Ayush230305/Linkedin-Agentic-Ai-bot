import os
import requests
from urllib.parse import urlencode

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"

def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    # State is generated and retained by the Streamlit session, then checked on callback.
    return AUTH_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile w_member_social",
        "state": state,
    })

def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=25,
    )
    if not response.ok:
        raise RuntimeError(f"Token exchange returned HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise RuntimeError("LinkedIn did not return an access token.")
    return access_token

def get_profile(access_token: str) -> dict:
    response = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(f"Profile lookup returned HTTP {response.status_code}: {response.text[:400]}")
    data = response.json()
    subject = data.get("sub")
    if not subject:
        raise RuntimeError("LinkedIn profile response did not contain a subject ID.")
    return {
        "id": subject,
        "author_urn": f"urn:li:person:{subject}",
        "name": data.get("name") or data.get("given_name") or "LinkedIn member",
    }

def publish_text_post(access_token: str, text: str, profile: dict) -> dict:
    if not profile or not profile.get("author_urn"):
        raise RuntimeError("Could not determine the LinkedIn member URN.")
    version = os.getenv("LINKEDIN_API_VERSION", "202601").strip()
    response = requests.post(
        POSTS_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "Linkedin-Version": version,
        },
        json={
            "author": profile["author_urn"],
            "commentary": text,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        },
        timeout=30,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"LinkedIn API returned HTTP {response.status_code}: {response.text[:700]}")
    return {"post_id": response.headers.get("x-restli-id", "Created; post ID unavailable")}
