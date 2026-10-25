"""
LinkPilot's ASI:One/Agentverse chat entry point.

This agent is the discoverable ACP interface: it can prepare a LinkedIn post from
the user's instructions. For actual publishing, use the local dashboard's explicit
approval step because LinkedIn OAuth tokens must remain with the account owner.
"""
import os
from datetime import datetime, timezone
from uuid import uuid4
from dotenv import load_dotenv
from openai import OpenAI
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, EndSessionContent, TextContent, chat_protocol_spec
)

load_dotenv()
api_key = os.getenv("ASI_ONE_API_KEY", "").strip()
if not api_key:
    raise RuntimeError("Set ASI_ONE_API_KEY in .env before starting agent.py")

client = OpenAI(base_url="https://api.asi1.ai/v1", api_key=api_key, timeout=45.0)
agent = Agent(
    name="LinkPilot Publishing Assistant",
    seed=os.getenv("UAGENT_SEED", "REPLACE_WITH_A_LONG_RANDOM_PRIVATE_SEED"),
    port=int(os.getenv("UAGENT_PORT", "8001")),
    mailbox=True,
    publish_agent_details=True,
)
protocol = Protocol(spec=chat_protocol_spec)

@protocol.on_message(model=ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg.msg_id
    ))
    prompt = "\n".join(
        item.text for item in msg.content if isinstance(item, TextContent)
    ).strip()
    if not prompt:
        answer = "Please send your process and the LinkedIn post or idea you want me to prepare."
    else:
        try:
            completion = client.chat.completions.create(
                model=os.getenv("ASI_ONE_MODEL", "asi1"),
                messages=[
                    {"role": "system", "content": (
                        "You are LinkPilot, an agent that turns a user's process and draft into "
                        "a clear LinkedIn post. Ask for missing process or draft details when needed. "
                        "Never claim that you published anything. This chat agent prepares and reviews "
                        "content; actual publishing requires the user to approve it in the LinkPilot dashboard. "
                        "Do not invent personal facts or results. Keep the post concise and authentic."
                    )},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=1200,
            )
            answer = (completion.choices[0].message.content or "").strip()
            if not answer:
                answer = "I couldn't prepare a post from that input. Please try again with more detail."
        except Exception as exc:
            ctx.logger.exception("ASI:One request failed")
            answer = f"Sorry, I couldn't reach the writing model. Check the ASI:One API key and connection. ({type(exc).__name__})"

    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(text=answer)],
    ))
    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[EndSessionContent()],
    ))

agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
