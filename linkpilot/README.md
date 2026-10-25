
# LinkPilot

An AI agent that turns plain-language instructions into reviewed,
editable LinkedIn posts and publishes them only after explicit approval.

## Problem

Writing professional LinkedIn posts takes time. Generic AI-generated
content can also contain unsupported claims or sound unlike the author.

## Solution

LinkPilot combines an LLM drafting step, a critic step, persistent draft
storage, human approval, and the official LinkedIn Posts API.

## Features

- Natural-language post generation
- Critic and improvement step
- Editable drafts with unique IDs
- Explicit approval before publication
- Official LinkedIn API integration
- uAgents and Agentverse integration
- Agent Chat Protocol for ASI:One
- Duplicate-publication protection

## Architecture

User -> ASI:One -> LinkPilot uAgent -> LLM
     -> Critic -> Pending draft -> Human approval
     -> LinkedIn Posts API -> Publication result

## Tech Stack

- Python
- uAgents
- Agentverse
- ASI:One / Agent Chat Protocol
- OpenAI-compatible LLM API
- SQLite
- LinkedIn Posts API

## Prerequisites

- Python 3.11
- Agentverse account
- ASI:One API access, if running locally
- LinkedIn developer application with approved posting access

## Setup

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

   pip install -r requirements.txt

4. Copy .env.example to .env.
5. Configure the LLM and LinkedIn credentials.
6. Complete the LinkedIn OAuth flow.
7. Run the local tests.
8. Start the agent:

   python agent.py

## Example conversation

User:
generate: Write a LinkedIn post about what I learned from my
first machine-learning project. Do not invent achievements.

Agent:
Returns a reviewed draft and its draft ID.

User:
edit DRAFT_ID: [replacement post text]

Agent:
Returns the revised preview. Nothing is published.

User:
approve DRAFT_ID

Agent:
Publishes the approved text and returns the LinkedIn post ID.

## Security

- Secrets are stored outside source control.
- Drafts have explicit states.
- Publishing requires owner authorization.
- Duplicate approvals are rejected.
- Ambiguous publication outcomes require manual verification.
- No scraping, automated likes, comments, or connection requests.

## Limitations

- LinkedIn access depends on application permissions.
- Token renewal may require reauthorization.
- Hosted persistence depends on the deployment environment.
- The critic does not guarantee factual accuracy.
- Writing-style learning and scheduling are future enhancements.

## Demo and Submission

Agentverse profile: [ADD URL]
ASI:One shared chat: [ADD URL]
Demo video: [ADD URL]
GitHub repository: [ADD URL]

## License

[CHOOSE A LICENSE]
