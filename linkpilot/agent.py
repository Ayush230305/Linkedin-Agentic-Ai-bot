import asyncio
import logging
import os

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("linkpilot")

AGENT_NAME = "LinkPilot"

AGENT_SEED = os.getenv("LINKPILOT_AGENT_SEED", "").strip()
AGENTVERSE_KEY = os.getenv("AGENTVERSE_KEY", "").strip()
AGENT_SEED_PHRASE = os.getenv("AGENT_SEED_PHRASE", "").strip()

if not AGENT_SEED:
    raise RuntimeError(
        "Missing LINKPILOT_AGENT_SEED in your .env file."
    )

# Fix: create an event loop before initializing Agent.
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

agent = Agent(
    name=AGENT_NAME,
    seed=AGENT_SEED,
    port=8000,
    endpoint=["http://localhost:8000/submit"],
)

chat_protocol = Protocol(spec=chat_protocol_spec)


@chat_protocol.on_message(model=ChatMessage)
async def handle_chat_message(
    ctx: Context,
    sender: str,
    msg: ChatMessage,
):
    ctx.logger.info("Received chat message from %s", sender)

    incoming_text = "\n".join(
        item.text
        for item in msg.content
        if isinstance(item, TextContent)
    ).strip()

    ctx.logger.info("Incoming message received.")

    reply = (
        "Hello! I'm LinkPilot. "
        "I can help prepare LinkedIn post ideas. "
        "AI generation, review, approval, and LinkedIn publishing "
        "are not connected in this starter agent yet."
    )

    response = ChatMessage(
        timestamp=ctx.timestamp,
        msg_id=ctx.new_msg_id(),
        content=[
            TextContent(
                type="text",
                text=reply,
            )
        ],
    )

    await ctx.send(sender, response)


@chat_protocol.on_message(model=ChatAcknowledgement)
async def handle_chat_acknowledgement(
    ctx: Context,
    sender: str,
    msg: ChatAcknowledgement,
):
    ctx.logger.info(
        "Chat acknowledgement received from %s",
        sender,
    )


agent.include(chat_protocol, publish_manifest=True)


if __name__ == "__main__":
    # Register only when both credentials are configured.
    if AGENTVERSE_KEY and AGENT_SEED_PHRASE:
        register_chat_agent(
            AGENT_NAME,
            "http://localhost:8000",
            active=True,
            credentials=RegistrationRequestCredentials(
                agentverse_api_key=AGENTVERSE_KEY,
                agent_seed_phrase=AGENT_SEED_PHRASE,
            ),
        )
        logger.info("Agentverse registration request submitted.")
    else:
        logger.warning(
            "Agentverse registration skipped. Set AGENTVERSE_KEY "
            "and AGENT_SEED_PHRASE in your .env file."
        )

    agent.run()
