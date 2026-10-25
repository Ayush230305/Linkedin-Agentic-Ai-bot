# LinkPilot — Fetch-A-Thon 3.0

LinkPilot turns a user's process and rough LinkedIn draft into a reviewed post, then publishes it only after explicit user approval.

## Features
- Streamlit dashboard for process instructions, post input, review, and publish approval.
- ASI:One (`https://api.asi1.ai/v1`) for draft preparation.
- LinkedIn OAuth authorization-code flow for member identity and posting.
- LinkedIn Posts API for text-only posts.
- SQLite activity history.
- Separate uAgents Chat Protocol agent for Agentverse/ASI:One discovery.

## Requirements
Use **Python 3.12** for the hackathon environment. Python 3.14 may not yet be compatible with all uAgents dependency wheels.

## Setup on Windows PowerShell

```powershell
cd D:\LinkPilot\linkpilot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `ASI_ONE_API_KEY`. To enable real publishing, create a LinkedIn Developer App, configure the redirect URL exactly as `http://localhost:8501`, and enter its client ID and secret. The app must have the appropriate Sign In with LinkedIn / OpenID Connect and Community Management API products/permissions, including `w_member_social`. Approval and availability are controlled by LinkedIn.

Run the UI:

```powershell
streamlit run app.py
```

Run the ACP agent in a **second terminal**:

```powershell
cd D:\LinkPilot\linkpilot
.\.venv\Scripts\Activate.ps1
python agent.py
```

Keep both processes running while testing.

## Safe test order
1. Test the UI with only `ASI_ONE_API_KEY`; prepare a draft and inspect it.
2. Configure LinkedIn OAuth and connect your own account.
3. Publish a harmless test post only after reading the final text and checking the confirmation box.
4. Verify the post on LinkedIn and inspect the Recent Activity section.
5. Register/deploy the ACP agent through Agentverse, enable its mailbox, confirm the manifest, and test it in ASI:One.

## Important notes
- The ACP agent can prepare content in ASI:One. The local dashboard owns the interactive LinkedIn OAuth session and publishing approval. The ACP agent intentionally does not claim to publish posts.
- LinkedIn can reject publishing if the app lacks required API access, the token expires, or the API version is no longer supported.
- Check the current LinkedIn API documentation and choose a supported `LINKEDIN_API_VERSION` before a public demo.
- OAuth state is checked against the current Streamlit session as a basic CSRF defense. For production, use a hardened server-side session store and review the entire OAuth flow. This starter is a hackathon MVP, not a production security review.
- Never commit `.env`, OAuth tokens, API keys, or your agent seed to GitHub.

## Hackathon checklist
- [ ] Agent registered on Agentverse and categorized under Innovation Lab as required by the event.
- [ ] ACP/ASI:One chat test succeeds.
- [ ] Dashboard creates and reviews a draft.
- [ ] LinkedIn publishing succeeds using approved OAuth permissions.
- [ ] Public GitHub repository and clear README.
- [ ] Public ASI:One shared-chat URL, Agentverse profile URL, and demo video included in submission.
